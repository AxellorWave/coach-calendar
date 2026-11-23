import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = os.getenv('LOG_DIR', '/app/logs')
LOG_KEEP_DAYS = int(os.getenv('LOG_KEEP_DAYS', '92'))  # ~3 месяца

_formatter = logging.Formatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

_configured = False


def _daily_file(filename: str, level: int) -> logging.Handler:
    # Текущий день пишется в <filename>, в полночь файл переименовывается
    # в <filename>.ГГГГ-ММ-ДД, файлы старше LOG_KEEP_DAYS дней удаляются.
    handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        when='midnight',
        backupCount=LOG_KEEP_DAYS,
        encoding='utf-8',
    )
    handler.setLevel(level)
    handler.setFormatter(_formatter)
    return handler


def _configure_root():
    global _configured
    if _configured:
        return
    _configured = True

    os.makedirs(LOG_DIR, exist_ok=True)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda r: r.levelno <= logging.INFO)
    stdout_handler.setFormatter(_formatter)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(_formatter)

    root = logging.getLogger()
    root.setLevel(logging.WARNING)  # сторонние библиотеки — только предупреждения и ошибки
    root.addHandler(stdout_handler)
    root.addHandler(stderr_handler)
    root.addHandler(_daily_file('bot.log', logging.DEBUG))       # всё подряд
    root.addHandler(_daily_file('errors.log', logging.WARNING))  # только WARNING и ERROR


def get_logger(name: str, level: int = logging.INFO):
    _configure_root()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
