import httplib2
from google.oauth2 import service_account
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from app.config import SERVICE_ACCOUNT_FILE

SCOPES = ['https://www.googleapis.com/auth/calendar']
HTTP_TIMEOUT = 20  # секунд; по умолчанию было 60, при зависшем соединении лучше быстрее уйти на повтор


def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    http = AuthorizedHttp(creds, http=httplib2.Http(timeout=HTTP_TIMEOUT))
    return build('calendar', 'v3', http=http, cache_discovery=False)
