import vk_api
from app.parser.message_parser import parse_message
from app.calendar.actions import create_event, delete_event, edit_event
from app.config import VK_PEER_ID
from app.vk.state import save_state
from app.logger import get_logger

logger = get_logger(__name__)


def handle_message(text: str):
    logger.info(f"Сообщение: {text}")
    result = parse_message(text)
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


def process_new_messages(vk: vk_api.vk_api.VkApiMethod, state: dict):
    last_id = state['last_id']

    if not last_id:
        resp = vk.messages.getHistory(
            peer_id=VK_PEER_ID,
            count=1
        )
        items = resp['items']
        if items:
            state['last_id'] = items[0]['id']
            save_state(state)
        return

    resp = vk.messages.getHistory(
        peer_id=VK_PEER_ID,
        count=200
    )
    items = resp['items']
    if not items:
        return

    items = list(reversed(items))
    new_items = [msg for msg in items if msg['id'] > last_id]

    for msg in new_items:
        if not msg.get('out'):
            handle_message(msg['text'])
        state['last_id'] = msg['id']
        save_state(state)
