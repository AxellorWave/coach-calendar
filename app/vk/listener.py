import os
import time
from datetime import datetime, timedelta

import requests
from vk_api.longpoll import VkEventType
from app.calendar.actions import TZ
from app.vk.client import get_vk_session, get_longpoll
from app.vk.handlers import process_new_messages
from app.vk.state import load_state, save_state
from app.sync import sync_calendar
from app.logger import get_logger

logger = get_logger(__name__)
get_logger("vk_api", level=30)

RECONNECT_DELAY = 5        # секунд до первого переподключения
RECONNECT_DELAY_MAX = 300  # максимум между попытками при долгом отсутствии сети
SYNC_HOUR = int(os.getenv('SYNC_HOUR', '4'))  # ежедневная сверка в это время (Мск)


def _next_sync_time(now: datetime) -> datetime:
    target = now.replace(hour=SYNC_HOUR, minute=0, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


def _run_sync(vk, state):
    logger.info("Сверка календаря с историей сообщений")
    try:
        last_id = sync_calendar(vk)
        if last_id and last_id > state.get('last_id', 0):
            state['last_id'] = last_id
            save_state(state)
    except Exception as e:
        logger.exception(f"Ошибка синхронизации с календарём: {e}")


def run():
    vk_session = get_vk_session()
    vk = vk_session.get_api()
    state = load_state()

    _run_sync(vk, state)
    next_sync = _next_sync_time(datetime.now(TZ))
    logger.info(f"Следующая сверка: {next_sync:%d-%m-%Y %H:%M}")

    delay = RECONNECT_DELAY
    while True:
        try:
            # При старте и после каждого обрыва догоняем сообщения,
            # пришедшие, пока соединения не было.
            process_new_messages(vk, state)
            longpoll = get_longpoll(vk_session)
            logger.info("Long Poll подключён")
            delay = RECONNECT_DELAY

            while True:
                # check() возвращается не позже чем через ~25 с, даже без событий,
                # поэтому между вызовами успеваем проверить расписание сверки.
                events = longpoll.check()
                if any(e.type == VkEventType.MESSAGE_NEW for e in events):
                    process_new_messages(vk, state)

                if datetime.now(TZ) >= next_sync:
                    _run_sync(vk, state)
                    next_sync = _next_sync_time(datetime.now(TZ))
                    logger.info(f"Следующая сверка: {next_sync:%d-%m-%Y %H:%M}")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.warning(f"Обрыв Long Poll ({type(e).__name__}), переподключение через {delay} с")
        except Exception as e:
            logger.exception(f"Ошибка Long Poll, переподключение через {delay} с: {e}")

        time.sleep(delay)
        delay = min(delay * 2, RECONNECT_DELAY_MAX)
