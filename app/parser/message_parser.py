import re
from app.logger import get_logger

logger = get_logger(__name__)

DT = r"(\d{2}\.\d{2}\.\d{4}) в (\d{2}:\d{2}) Мск"
TAIL = r", (.+?)\.\s*Специальность:\s*'([^']+)'\."

PATTERN_CREATE = re.compile(r"Запись на сессию\.\s*" + DT + TAIL)
PATTERN_EDIT_OLD = re.compile(
    r"Перенос сессии\.\s*С (\d{2}\.\d{2}\.\d{4}) (\d{2}:\d{2}) Мск на " + DT + TAIL
)
PATTERN_EDIT_NEW = re.compile(r"Перенос записи\.\s*Новое время:\s*" + DT + TAIL)
PATTERN_DELETE = re.compile(r"Отмена (?:сессии|записи)\.\s*" + DT + TAIL)


def parse_message(text: str) -> dict | None:
    try:
        text = text.strip()

        if m := PATTERN_CREATE.match(text):
            return {
                'type': 'create',
                'date': m.group(1).replace('.', '-'),
                'time': m.group(2),
                'name': m.group(3).strip(),
                'session_type': m.group(4).strip()
            }

        if m := PATTERN_EDIT_OLD.match(text):
            return {
                'type': 'edit',
                'date_old': m.group(1).replace('.', '-'),
                'time_old': m.group(2),
                'date_new': m.group(3).replace('.', '-'),
                'time_new': m.group(4),
                'name': m.group(5).strip(),
                'session_type': m.group(6).strip()
            }

        if m := PATTERN_EDIT_NEW.match(text):
            return {
                'type': 'edit',
                'date_old': None,
                'time_old': None,
                'date_new': m.group(1).replace('.', '-'),
                'time_new': m.group(2),
                'name': m.group(3).strip(),
                'session_type': m.group(4).strip()
            }

        if m := PATTERN_DELETE.match(text):
            return {
                'type': 'delete',
                'date': m.group(1).replace('.', '-'),
                'time': m.group(2),
                'name': m.group(3).strip(),
                'session_type': m.group(4).strip()
            }

        logger.warning(f'Неподходящее сообщение: {text[:200]!r}')
        return None

    except Exception as e:
        logger.exception(f"Ошибка парсинга: {e}")
        return None