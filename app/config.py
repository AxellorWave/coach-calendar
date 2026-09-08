import os
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN")
VK_PEER_ID = int(os.getenv("VK_PEER_ID"))
STATE_FILE = os.getenv("STATE_FILE", "state.json")

CALENDAR_ID = os.getenv("CALENDAR_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
