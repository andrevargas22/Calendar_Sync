"""Google Calendar functions."""
from datetime import datetime, timedelta
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pathlib import Path
import csv

from src.logger import logger
from src.config import SCOPES, CALENDAR_ID, CREDENTIALS_JSON, TIMEZONE, CACHE_FILE
from src.utils import parse_datetime

def get_calendar_service():
    """
    Initialize the Calendar API using Service Account.
    
    Returns:
        Google Calendar API service
    """
    try:
        if not CREDENTIALS_JSON:
            raise ValueError("GOOGLE_CREDENTIALS environment variable not found")
        credentials_info = json.loads(CREDENTIALS_JSON)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES
        )
        
        return build('calendar', 'v3', credentials=credentials)
    except Exception as e:
        logger.error(f"❌ Error authenticating with Service Account: {e}")
        raise

def get_google_events(svc, start, end):
    """
    Fetch events from Google Calendar in the given period.
    
    Args:
        svc: Google Calendar API service
        start: Start datetime
        end: End datetime
        
    Returns:
        List of events
    """
    extended_end = end + timedelta(days=1)
    evs = svc.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start.isoformat()+'Z',
        timeMax=extended_end.isoformat()+'Z',
        singleEvents=True, 
        orderBy='startTime',
        maxResults=2500
    ).execute().get('items',[])
    
    out = []
    for ev in evs:
        s = ev['start'].get('dateTime') or ev['start'].get('date')
        f = ev['end'].get('dateTime') or ev['end'].get('date')
        s = datetime.fromisoformat(s.replace('Z',''))
        f = datetime.fromisoformat(f.replace('Z',''))
        if s.tzinfo is not None:
            s = s.astimezone().replace(tzinfo=None)
        if f.tzinfo is not None:
            f = f.astimezone().replace(tzinfo=None)
        out.append({'titulo':ev.get('summary'), 'inicio':s, 'fim':f})
    
    return out

def criar_evento_google(svc, ev):
    """
    Create an event in Google Calendar.
    
    Args:
        svc: Google Calendar API service
        ev: Event dictionary
    """
    body = {
        'summary': ev['titulo'],
        'start': {'dateTime': ev['inicio'], 'timeZone': TIMEZONE},
        'end':   {'dateTime': ev['fim'],    'timeZone': TIMEZONE},
    }
    svc.events().insert(calendarId=CALENDAR_ID, body=body).execute()
    logger.info(f"Created in Google Calendar: {ev['titulo']} ({ev['inicio']} - {ev['fim']})")

def remover_evento_google_by_id(svc, event_id, event_title, event_start, event_end):
    """
    Remove an event from Google Calendar by ID.
    
    Args:
        svc: Google Calendar API service
        event_id: Google Calendar event ID
        event_title: Event title (for logging)
        event_start: Event start time (for logging)
        event_end: Event end time (for logging)
        
    Returns:
        bool: True if deleted successfully
    """
    try:
        svc.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        logger.info(f"Deleted event from Google Calendar: {event_title} ({event_start} - {event_end})")
        return True
    except Exception as e:
        logger.error(f"Error deleting event {event_title}: {e}")
        return False

def buscar_e_deletar_cancelados(svc):
    """
    Find and delete all 'Cancelado:' events and their original pairs.
    
    Args:
        svc: Google Calendar API service
    """
    from src.config import DAYS_BEFORE, DAYS_AFTER
    
    now = datetime.now()
    start_search = now - timedelta(days=DAYS_BEFORE)
    end_search = now + timedelta(days=DAYS_AFTER)
    
    events = svc.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_search.isoformat()+'Z',
        timeMax=end_search.isoformat()+'Z',
        singleEvents=True,
        maxResults=2500
    ).execute().get('items', [])
    
    # Index by (title, start, end)
    event_map = {}
    for ev in events:
        title = ev.get('summary', '')
        s = ev['start'].get('dateTime') or ev['start'].get('date')
        f = ev['end'].get('dateTime') or ev['end'].get('date')
        s_dt = parse_datetime(s)
        f_dt = parse_datetime(f)
        event_map.setdefault((title, s_dt, f_dt), []).append(ev)

    to_delete = set()
    cache_to_remove = set()
    for (title, s_dt, f_dt), ev_list in event_map.items():
        if title.startswith("Cancelado:"):
            # Always delete the canceled event
            to_delete.add(ev_list[0]['id'])
            cache_to_remove.add((title, s_dt.isoformat(sep='T'), f_dt.isoformat(sep='T')))
            
            # Try to find and delete the original event too
            original_title = title.replace("Cancelado:", "").strip()
            original_key = (original_title, s_dt, f_dt)
            if original_key in event_map:
                to_delete.add(event_map[original_key][0]['id'])
                cache_to_remove.add((original_title, s_dt.isoformat(sep='T'), f_dt.isoformat(sep='T')))
                logger.info(f"Found cancel pair, will delete both: '{title}' and '{original_title}' at {s_dt}")
            else:
                logger.info(f"Deleting cancelado event (no pair found): '{title}' at {s_dt}")

    # Delete events from Google Calendar
    for event_id in to_delete:
        for ev in events:
            if ev['id'] == event_id:
                event_title = ev.get('summary', '')
                event_start = ev['start'].get('dateTime') or ev['start'].get('date')
                event_end = ev['end'].get('dateTime') or ev['end'].get('date')
                remover_evento_google_by_id(svc, event_id, event_title, event_start, event_end)
                break

    # Remove from local cache if using local file
    if cache_to_remove and Path(CACHE_FILE).exists():
        cache = set()
        with open(CACHE_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cache.add((row['titulo'], row['inicio'], row['fim']))
        
        # Remove marked events
        cache = {item for item in cache if item not in cache_to_remove}
        with open(CACHE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['titulo', 'inicio', 'fim'])
            writer.writeheader()
            for titulo, inicio, fim in cache:
                writer.writerow({'titulo': titulo, 'inicio': inicio, 'fim': fim})
        
        logger.info(f"Removed {len(cache_to_remove)} events from cache.")