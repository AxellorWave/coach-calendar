from datetime import datetime, timedelta
import pytz
from app.logger import get_logger
from app.calendar.service import get_calendar_service
from app.config import CALENDAR_ID

logger = get_logger(__name__)

SESSION_TYPES = {
    'Коуч': 'Коуч-сессия',
    'Психолог (гайд-сессия)': 'Гайд-сессия'
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

        return service.events().insert(calendarId=CALENDAR_ID, body=event).execute()

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

        for event in events:
            summary = event.get('summary', '')
            if name in summary:
                service.events().delete(calendarId=CALENDAR_ID, eventId=event['id']).execute()
                return True

        return False

    except Exception as e:
        logger.exception(f"Ошибка удаления: {e}")
        return False


def edit_event(name, old_dt, new_dt, session_type):
    if delete_event(name, old_dt, session_type):
        return create_event(name, new_dt, session_type)
    return None
