from datetime import datetime, timedelta
import pytz
from app.logger import get_logger
from app.calendar.service import get_calendar_service
from app.config import CALENDAR_ID

logger = get_logger(__name__)

SESSION_TYPES = {
    'Коуч': 'Коуч-сессия',
    'Психолог (гайд-сессия)': 'Гайд-сессия',
    'Психолог': 'Психолог'
}


def create_event(name: str, start_datetime: str, session_type: str):
    try:
        service = get_calendar_service()

        if session_type not in SESSION_TYPES:
            logger.error("Неизвестный тип сессии")
            return None

        summary = f'⭐️ {SESSION_TYPES[session_type]} {name} Просебя'

        dt = datetime.strptime(start_datetime, '%d-%m-%Y %H:%M')
        start = dt.isoformat()
        end = (dt + timedelta(hours=1)).isoformat()

        event = {
            'summary': summary,
            'start': {'dateTime': start, 'timeZone': 'Europe/Moscow'},
            'end': {'dateTime': end, 'timeZone': 'Europe/Moscow'},
        }

        event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        logger.info(f'Событие "{summary}" на ({start_datetime}) создано: {event.get("htmlLink")}')
        return event
    except Exception as e:
        logger.exception(f"Ошибка создания события: {e}")
        return None


def delete_event(name, start_datetime, session_type):
    try:
        service = get_calendar_service()
        timezone = pytz.timezone('Europe/Moscow')

        target = timezone.localize(datetime.strptime(start_datetime, '%d-%m-%Y %H:%M'))

        events = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=(target - timedelta(minutes=5)).isoformat(),
            timeMax=(target + timedelta(minutes=5)).isoformat(),
            singleEvents=True,
            orderBy='startTime',
        ).execute().get('items', [])

        if session_type not in SESSION_TYPES:
            logger.exception(f"Ошибка при распозновании типа сессии")
            return {'error': 'Ошибка при распозновании типа сессии'}

        session_type = SESSION_TYPES[session_type]
        for event in events:
            summary = event.get('summary', '')
            if name in summary and session_type in summary:
                logger.info(f'Событие "{summary}" ({start_datetime}) удалено')
                service.events().delete(calendarId=CALENDAR_ID, eventId=event['id']).execute()
                return True
        logger.warning(f'Событие {session_type} {name} в {target} не найдено')
        return False

    except Exception as e:
        logger.exception(f"Ошибка удаления: {e}")
        return False


SEARCH_FORWARD = timedelta(days=90)
SEARCH_BACK = timedelta(days=30)
TZ = pytz.timezone('Europe/Moscow')


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


def _move_nearest_event(name, new_dt, session_type):
    try:
        if session_type not in SESSION_TYPES:
            logger.error('Неизвестный тип сессии')
            return False
        label = SESSION_TYPES[session_type]
        service = get_calendar_service()

        new_start = TZ.localize(datetime.strptime(new_dt, '%d-%m-%Y %H:%M'))
        now = datetime.now(TZ)

        future = _find_events(service, name, label, now, now + SEARCH_FORWARD)

        if any(_event_start(e) == new_start for e in future):
            logger.info(f'{label} {name} уже стоит на {new_dt}, перенос не нужен')
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
        service.events().patch(
            calendarId=CALENDAR_ID,
            eventId=event['id'],
            body={
                'start': {'dateTime': new_start.isoformat(), 'timeZone': 'Europe/Moscow'},
                'end': {'dateTime': (new_start + timedelta(hours=1)).isoformat(), 'timeZone': 'Europe/Moscow'},
            },
        ).execute()
        logger.info(f'Запись {label} "{name}" перенесена с ({old_start}) на ({new_dt})')
        return True

    except Exception as e:
        logger.exception(f'Ошибка переноса: {e}')
        return False


def edit_event(name, old_dt, new_dt, session_type):
    if not old_dt or 'None' in str(old_dt):
        return _move_nearest_event(name, new_dt, session_type)

    if delete_event(name, old_dt, session_type):
        if create_event(name, new_dt, session_type):
            logger.info(f'Запись {session_type} на имя "{name}" успешно перенесена с ({old_dt}) на ({new_dt})')
            return True
    logger.error('Ошибка переноса')
    return False