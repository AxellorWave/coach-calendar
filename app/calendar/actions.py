from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta
import pytz
from app.logger import get_logger
from app.calendar.service import get_calendar_service
from app.config import CALENDAR_ID
from app.retry import with_retries

logger = get_logger(__name__)

SESSION_TYPES = {
    'Коуч': 'Коуч-сессия',
    'Психолог (гайд-сессия)': 'Гайд-сессия',
    'Психолог': 'Психолог'
}

TZ = pytz.timezone('Europe/Moscow')
SEARCH_FORWARD = timedelta(days=90)
SEARCH_BACK = timedelta(days=30)
SLOT_TOLERANCE = timedelta(minutes=5)

# В режиме сверки не пишем в лог действия, которые ничего не изменили
# («уже есть», «уже удалено», «перенос не нужен») — их там сотни.
_quiet_noops = ContextVar('quiet_noops', default=False)


@contextmanager
def quiet_noops():
    token = _quiet_noops.set(True)
    try:
        yield
    finally:
        _quiet_noops.reset(token)


def _log_noop(msg):
    if not _quiet_noops.get():
        logger.info(msg)


def _find_at(service, name, label, start):
    events = service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=(start - SLOT_TOLERANCE).isoformat(),
        timeMax=(start + SLOT_TOLERANCE).isoformat(),
        singleEvents=True,
        orderBy='startTime',
    ).execute().get('items', [])
    for event in events:
        summary = event.get('summary', '')
        if name in summary and label in summary:
            return event
    return None


def _parse_dt(start_datetime):
    return TZ.localize(datetime.strptime(start_datetime, '%d-%m-%Y %H:%M'))


# Все операции ниже идемпотентны (сначала ищут событие, потом действуют),
# поэтому их безопасно повторять целиком при сетевых ошибках: повтор
# после «тихо успевшего» insert найдёт уже созданное событие, а не задвоит его.

@with_retries('Создание события')
def _create_event(name, start_datetime, label):
    service = get_calendar_service()
    start = _parse_dt(start_datetime)

    existing = _find_at(service, name, label, start)
    if existing:
        _log_noop(f'Событие {label} {name} на ({start_datetime}) уже есть, пропускаю')
        return existing

    summary = f'⭐️ {label} {name} Просебя'
    event = {
        'summary': summary,
        'start': {'dateTime': start.isoformat(), 'timeZone': 'Europe/Moscow'},
        'end': {'dateTime': (start + timedelta(hours=1)).isoformat(), 'timeZone': 'Europe/Moscow'},
    }

    event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    logger.info(f'Событие "{summary}" на ({start_datetime}) создано: {event.get("htmlLink")}')
    return event


def create_event(name: str, start_datetime: str, session_type: str):
    if session_type not in SESSION_TYPES:
        logger.error(f"Неизвестный тип сессии: {session_type!r}")
        return None
    try:
        return _create_event(name, start_datetime, SESSION_TYPES[session_type])
    except Exception as e:
        logger.exception(f'НЕ СОЗДАНО событие {session_type} {name} на ({start_datetime}): {e}')
        return None


@with_retries('Удаление события')
def _delete_event(name, start_datetime, label):
    service = get_calendar_service()

    event = _find_at(service, name, label, _parse_dt(start_datetime))
    if not event:
        _log_noop(f'Событие {label} {name} на ({start_datetime}) не найдено — уже удалено')
        return True

    service.events().delete(calendarId=CALENDAR_ID, eventId=event['id']).execute()
    logger.info(f'Событие "{event.get("summary", "")}" ({start_datetime}) удалено')
    return True


def delete_event(name, start_datetime, session_type):
    if session_type not in SESSION_TYPES:
        logger.error(f"Неизвестный тип сессии: {session_type!r}")
        return {'error': 'Ошибка при распозновании типа сессии'}
    try:
        return _delete_event(name, start_datetime, SESSION_TYPES[session_type])
    except Exception as e:
        logger.exception(f'НЕ УДАЛЕНО событие {session_type} {name} ({start_datetime}): {e}')
        return False


def _find_events(service, name, label, time_min, time_max):
    found, page_token = [], None
    while True:
        resp = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy='startTime',
            q=name,
            pageToken=page_token,
        ).execute()
        for ev in resp.get('items', []):
            summary = ev.get('summary', '')
            if name in summary and label in summary:
                found.append(ev)
        page_token = resp.get('nextPageToken')
        if not page_token:
            return found


def _event_start(ev):
    raw = ev.get('start', {}).get('dateTime')
    return datetime.fromisoformat(raw.replace('Z', '+00:00')) if raw else None


@with_retries('Перенос события')
def _move_nearest(name, new_dt, session_type, label):
    service = get_calendar_service()

    new_start = TZ.localize(datetime.strptime(new_dt, '%d-%m-%Y %H:%M'))
    now = datetime.now(TZ)

    future = _find_events(service, name, label, now, now + SEARCH_FORWARD)

    if any(_event_start(e) == new_start for e in future):
        _log_noop(f'{label} {name} уже стоит на {new_dt}, перенос не нужен')
        return True

    event = future[0] if future else None
    if event is None:
        past = _find_events(service, name, label, now - SEARCH_BACK, now)
        past = [e for e in past if _event_start(e) != new_start]
        event = past[-1] if past else None

    if event is None:
        logger.warning(f'{label} {name}: старое событие не найдено, создаю новое на {new_dt}')
        return bool(create_event(name, new_dt, session_type))

    old_start = _event_start(event)
    _patch_time(service, event, new_start)
    logger.info(f'Запись {label} "{name}" перенесена с ({old_start}) на ({new_dt})')
    return True


def _move_nearest_event(name, new_dt, session_type):
    if session_type not in SESSION_TYPES:
        logger.error(f'Неизвестный тип сессии: {session_type!r}')
        return False
    try:
        return _move_nearest(name, new_dt, session_type, SESSION_TYPES[session_type])
    except Exception as e:
        logger.exception(f'НЕ ПЕРЕНЕСЕНО {session_type} {name} на ({new_dt}): {e}')
        return False


def _patch_time(service, event, new_start):
    service.events().patch(
        calendarId=CALENDAR_ID,
        eventId=event['id'],
        body={
            'start': {'dateTime': new_start.isoformat(), 'timeZone': 'Europe/Moscow'},
            'end': {'dateTime': (new_start + timedelta(hours=1)).isoformat(), 'timeZone': 'Europe/Moscow'},
        },
    ).execute()


@with_retries('Перенос события')
def _edit_event(name, old_dt, new_dt, session_type, label):
    service = get_calendar_service()
    new_start = _parse_dt(new_dt)

    old_event = _find_at(service, name, label, _parse_dt(old_dt))
    new_event = _find_at(service, name, label, new_start)

    if new_event:
        if old_event and old_event['id'] != new_event['id']:
            service.events().delete(calendarId=CALENDAR_ID, eventId=old_event['id']).execute()
        _log_noop(f'{label} {name} уже стоит на ({new_dt}), перенос не нужен')
        return True

    if old_event:
        _patch_time(service, old_event, new_start)
        logger.info(f'Запись {label} "{name}" перенесена с ({old_dt}) на ({new_dt})')
        return True

    logger.warning(f'{label} {name}: на ({old_dt}) события нет, создаю на ({new_dt})')
    return bool(create_event(name, new_dt, session_type))


def edit_event(name, old_dt, new_dt, session_type):
    if not old_dt or 'None' in str(old_dt):
        return _move_nearest_event(name, new_dt, session_type)

    if session_type not in SESSION_TYPES:
        logger.error(f'Неизвестный тип сессии: {session_type!r}')
        return False
    try:
        return _edit_event(name, old_dt, new_dt, session_type, SESSION_TYPES[session_type])
    except Exception as e:
        logger.exception(f'НЕ ПЕРЕНЕСЕНО {session_type} {name} с ({old_dt}) на ({new_dt}): {e}')
        return False
