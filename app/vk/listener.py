from vk_api.longpoll import VkEventType
from app.vk.client import get_vk_session, get_longpoll
from app.vk.handlers import process_new_messages
from app.vk.state import load_state
from app.logger import get_logger

logger = get_logger(__name__)
get_logger("vk_api", level=30)

def run():
    vk_session = get_vk_session()
    vk = vk_session.get_api()
    state = load_state()

    process_new_messages(vk, state)

    longpoll = get_longpoll(vk_session)
    logger.info("Бот запущен")

    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW:
                    process_new_messages(vk, state)
        except Exception as e:
            logger.exception(f"Обрыв Long Poll, переподключаюсь: {e}")
