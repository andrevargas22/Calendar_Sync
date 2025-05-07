import os
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Config
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS')

def get_calendar_service():
    credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not credentials_json:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found")
    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=credentials)

def get_period():
    hoje = datetime.now()
    seg_atual = hoje - timedelta(days=hoje.weekday())
    start = seg_atual.replace(hour=7, minute=0, second=0, microsecond=0)
    end = (seg_atual + timedelta(days=11)).replace(hour=18, minute=0, second=0, microsecond=0)
    return start, end

def delete_events_in_period(svc, start, end):
    print(f"Deleting events from {start} to {end} ...")
    events = svc.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start.isoformat()+'Z',
        timeMax=end.isoformat()+'Z',
        singleEvents=True,
        maxResults=2500
    ).execute().get('items', [])
    print(f"Found {len(events)} events to delete.")
    for ev in events:
        event_id = ev['id']
        summary = ev.get('summary', '')
        start_time = ev['start'].get('dateTime') or ev['start'].get('date')
        end_time = ev['end'].get('dateTime') or ev['end'].get('date')
        try:
            svc.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
            print(f"Deleted: {summary} ({start_time} - {end_time})")
        except Exception as e:
            print(f"Failed to delete {summary}: {e}")

def main():
    svc = get_calendar_service()
    start, end = get_period()
    delete_events_in_period(svc, start, end)

if __name__ == "__main__":
    main()
