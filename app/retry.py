import time
from functools import wraps

from googleapiclient.errors import HttpError

from app.logger import get_logger

logger = get_logger(__name__)

ATTEMPTS = 5
BASE_DELAY = 3  # секунды: 3, 6, 12, 24 между попытками


def _transient(e: BaseException) -> bool:
    """Ошибки, которые имеет смысл повторить: сеть, таймауты, 429 и 5xx от Google."""
    if isinstance(e, HttpError):
        return e.resp.status in (408, 429, 500, 502, 503, 504)
    try:
        import httplib2
        if isinstance(e, httplib2.HttpLib2Error):
            return True
    except ImportError:
        pass
    try:
        from google.auth.exceptions import TransportError
        if isinstance(e, TransportError):
            return True
    except ImportError:
        pass
    # TimeoutError, ConnectionError, ssl.SSLError, socket.gaierror — всё это OSError
    return isinstance(e, OSError)


def with_retries(what: str):
    """Повторяет функцию до ATTEMPTS раз при временных (сетевых) ошибках.

    Функция должна быть идемпотентной: повторный вызов после частичного
    успеха не должен создавать дубликатов.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, ATTEMPTS + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    if not _transient(e) or attempt == ATTEMPTS:
                        raise
                    delay = BASE_DELAY * 2 ** (attempt - 1)
                    logger.warning(
                        f'{what}: попытка {attempt}/{ATTEMPTS} не удалась '
                        f'({type(e).__name__}: {e}), повтор через {delay} с'
                    )
                    time.sleep(delay)
        return wrapper
    return decorator
