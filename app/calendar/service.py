from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.config import SERVICE_ACCOUNT_FILE

SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=creds)
