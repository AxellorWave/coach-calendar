import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_DIR = os.getenv('LOG_DIR', '/app/logs')

_formatter = logging.Formatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

_file_handler = None


def _get_file_handler():
    global _file_handler
    if _file_handler is None:
        os.makedirs(LOG_DIR, exist_ok=True)
        _file_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, 'bot.log'),
            maxBytes=5 * 1024 * 1024,  # 5 МБ на файл
            backupCount=5,             # bot.log.1 ... bot.log.5
            encoding='utf-8',
        )
        _file_handler.setLevel(logging.DEBUG)
        _file_handler.setFormatter(_formatter)
    return _file_handler


def get_logger(name: str, level: int = logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(lambda r: r.levelno <= logging.INFO)
    stdout_handler.setFormatter(_formatter)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(_formatter)

    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
    logger.addHandler(_get_file_handler())

    return logger