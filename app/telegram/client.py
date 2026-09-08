from telethon import TelegramClient
from app.config import API_ID, API_HASH


def get_client():
    return TelegramClient('session', API_ID, API_HASH, catch_up=True)
