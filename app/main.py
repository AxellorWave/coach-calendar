import asyncio
import logging
from app.telegram.client import get_client
from app.telegram.handlers import register_handlers
from app.config import PHONE_NUMBER
from app.logger import get_logger

logger = get_logger(__name__)
get_logger("telethon", level=logging.WARNING)


async def main():
    client = get_client()
    register_handlers(client)

    await client.start(PHONE_NUMBER)
    logger.info("Бот запущен")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
