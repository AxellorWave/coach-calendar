from telethon import events
from app.parser.message_parser import parse_message
from app.calendar.actions import create_event, delete_event, edit_event
from app.config import CHAT_ID
from app.logger import get_logger

logger = get_logger(__name__)


def register_handlers(client):
    @client.on(events.NewMessage(incoming=True, chats=CHAT_ID))
    async def handler(event):
        logger.info(f"Сообщение: {event.text}")
        result = parse_message(event.text)
        if not result:
            return

        if result['type'] == 'create':
            create_event(result['name'], f"{result['date']} {result['time']}", result['session_type'])
        elif result['type'] == 'edit':
            edit_event(
                result['name'],
                f"{result['date_old']} {result['time_old']}",
                f"{result['date_new']} {result['time_new']}",
                result['session_type']
            )

        elif result['type'] == 'delete':
            delete_event(result['name'], f"{result['date']} {result['time']}", result['session_type'])
