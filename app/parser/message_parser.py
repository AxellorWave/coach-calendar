import re
from app.logger import get_logger

logger = get_logger(__name__)


def parse_message(text: str) -> dict | None:
    try:
        pattern_create = r'^Запись на сессию\.\s*(\d{2}\.\d{2}\.\d{4}) в (\d{2}:\d{2}) Мск, ([^.]*?)\.\s*Специальность: \'([^.]*?)\'\.$'
        pattern_edit = r'^Перенос сессии\.\s*С (\d{2}\.\d{2}\.\d{4}) (\d{2}:\d{2}) Мск на (\d{2}\.\d{2}\.\d{4}) в (\d{2}:\d{2}) Мск, ([^.]*?)\.\s*Специальность: \'([^.]*?)\'\.$'
        pattern_delete = r'^Отмена сессии\.\s*(\d{2}\.\d{2}\.\d{4}) в (\d{2}:\d{2}) Мск, ([^.]*?)\.\s*Специальность: \'([^.]*?)\'\.$'

        if m := re.fullmatch(pattern_create, text):
            return {
                'type': 'create',
                'date': m.group(1).replace('.', '-'),
                'time': m.group(2),
                'name': m.group(3).strip(),
                'session_type': m.group(4).strip()
            }

        if m := re.fullmatch(pattern_edit, text):
            return {
                'type': 'edit',
                'date_old': m.group(1).replace('.', '-'),
                'time_old': m.group(2),
                'date_new': m.group(3).replace('.', '-'),
                'time_new': m.group(4),
                'name': m.group(5).strip(),
                'session_type': m.group(6).strip()
            }

        if m := re.fullmatch(pattern_delete, text):
            return {
                'type': 'delete',
                'date': m.group(1).replace('.', '-'),
                'time': m.group(2),
                'name': m.group(3).strip(),
                'session_type': m.group(4).strip()
            }
        logger.warning(f'Неподходящее сообщение')
        return None

    except Exception as e:
        logger.exception(f"Ошибка парсинга: {e}")
        return None
