"""
Google Calendar functions.
"""

from datetime import datetime, timedelta
import json
import time
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.logger import logger
from src.config import SCOPES, CALENDAR_ID, GOOGLE_SERVICE_ACCOUNT_KEY, TIMEZONE
    
    
def get_calendar_service():
    """
    Initialize the Calendar API using Service Account.
    
    Returns:
        Google Calendar API service
        
    Raises:
        ValueError: If credentials are missing or invalid
        json.JSONDecodeError: If credentials JSON is malformed
        Exception: If authentication fails
    """
    try:
        if not GOOGLE_SERVICE_ACCOUNT_KEY:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_KEY environment variable is not set")
        
 
        logger.info("Initializing Google Calendar API service...")
        credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_KEY)
        required_keys = {"type", "project_id", "private_key", "client_email"}
        missing = [k for k in required_keys if k not in credentials_info or not credentials_info.get(k)]
        if missing:
            raise ValueError(f"Service account credentials missing required fields: {missing}")
        
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES
        )

        service = build('calendar', 'v3', credentials=credentials)
        logger.info("Google Calendar API service initialized successfully")
        return service
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in service account credentials: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}")

def _retry(callable_fn, *, max_attempts=4, base_delay=0.5, op_name="api_call"):
    """Simple exponential backoff retry for transient Google API errors."""
    attempt = 0
    while True:
        try:
            return callable_fn()
        except HttpError as e:
            status = getattr(e.resp, 'status', None)
            if status in {429, 500, 502, 503, 504} and attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt) * (1 + random.random()*0.25)
                logger.warning(f"Transient error {status} during {op_name}, retrying in {delay:.2f}s (attempt {attempt+1}/{max_attempts})")
                time.sleep(delay)
                attempt += 1
                continue
            raise
        except Exception:
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt) * (1 + random.random()*0.25)
                logger.warning(f"Error during {op_name}, retrying in {delay:.2f}s (attempt {attempt+1}/{max_attempts})")
                time.sleep(delay)
                attempt += 1
                continue
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
        
    Raises:
        HttpError: If Google Calendar API request fails
        Exception: If data processing fails
    """
    try:
        extended_end = end + timedelta(days=1)
        logger.info(f"Fetching Google Calendar events from {start.date()} to {extended_end.date()}")
        
        def _list_call():
            return svc.events().list(
                calendarId=CALENDAR_ID,
                timeMin=start.isoformat()+'Z',
                timeMax=extended_end.isoformat()+'Z',
                singleEvents=True,
                orderBy='startTime',
                maxResults=2500
            ).execute()
        evs = _retry(_list_call, op_name="events.list").get('items', [])
        
        logger.info(f"Retrieved {len(evs)} raw events from Google Calendar")
        
        out = []
        for ev in evs:
            try:
                s = ev['start'].get('dateTime') or ev['start'].get('date')
                f = ev['end'].get('dateTime') or ev['end'].get('date')
                
                if not s or not f:
                    logger.warning(f"Event with ID {ev.get('id', 'unknown')[:8]}... has missing start/end times, skipping")
                    continue
                
                s = datetime.fromisoformat(s.replace('Z',''))
                f = datetime.fromisoformat(f.replace('Z',''))
                
                if s.tzinfo is not None:
                    s = s.astimezone().replace(tzinfo=None)
                if f.tzinfo is not None:
                    f = f.astimezone().replace(tzinfo=None)
                    
                out.append({
                    'id': ev.get('id'),
                    'titulo': ev.get('summary', 'Untitled Event'),
                    'inicio': s,
                    'fim': f
                })
            except Exception as e:
                event_id_partial = ev.get('id', 'unknown')[:8] if ev.get('id') else 'unknown'
                logger.warning(f"Error processing event {event_id_partial}...: {e}")
                continue
        
        logger.info(f"Successfully processed {len(out)} events")
        return out
        
    except HttpError as e:
        logger.error(f"Google Calendar API error: {e}")
        if e.resp.status == 403:
            logger.error("Permission denied. Check if the service account has calendar access")
        elif e.resp.status == 404:
            logger.error("Calendar not found. Check your GOOGLE_CALENDAR_ID configuration")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching events: {e}")
        raise

def criar_evento_google(svc, ev):
    """
    Create an event in Google Calendar with improved error handling.
    
    Args:
        svc: Google Calendar API service
        ev: Event dictionary with keys 'titulo', 'inicio', 'fim'
        
    Raises:
        HttpError: If Google Calendar API request fails
        ValueError: If event data is invalid
        Exception: If unexpected error occurs
    """
    try:
        # Validate event data
        required_fields = ['titulo', 'inicio', 'fim']
        missing_fields = [field for field in required_fields if not ev.get(field)]
        if missing_fields:
            raise ValueError(f"Event missing required fields: {missing_fields}")
        
        body = {
            'summary': ev['titulo'],
            'start': {'dateTime': ev['inicio'], 'timeZone': TIMEZONE},
            'end': {'dateTime': ev['fim'], 'timeZone': TIMEZONE},
        }
        
        logger.debug(f"Creating event: {ev['titulo']}")
        def _insert_call():
            return svc.events().insert(calendarId=CALENDAR_ID, body=body).execute()
        result = _retry(_insert_call, op_name="events.insert")
        
        event_id = result.get('id', 'unknown')
        logger.info(f"Created event in Google Calendar: {ev['titulo']} (ID: {event_id[:8]}...)")
        
    except HttpError as e:
        logger.error(f"Google Calendar API error creating event '{ev.get('titulo', 'unknown')}': {e}")
        if e.resp.status == 403:
            logger.error("Permission denied. Check if the service account can create events")
        elif e.resp.status == 404:
            logger.error("Calendar not found. Check your GOOGLE_CALENDAR_ID configuration")
        raise
    except ValueError as e:
        logger.error(f"Invalid event data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating event: {e}")
        raise

def remover_evento_google_by_id(svc, event_id, event_title, event_start, event_end):
    """
    Remove an event from Google Calendar by ID with improved error handling.
    
    Args:
        svc: Google Calendar API service
        event_id: Google Calendar event ID
        event_title: Event title (for logging)
        event_start: Event start time (for logging)
        event_end: Event end time (for logging)
        
    Returns:
        bool: True if deleted successfully, False otherwise
        
    Raises:
        Exception: Only if critical error occurs
    """
    try:
        if not event_id:
            logger.warning(f"Cannot delete event '{event_title}': missing event ID")
            return False
        
        event_id_partial = event_id[:8] if len(event_id) > 8 else event_id
        logger.debug(f"Deleting event: {event_title} (ID: {event_id_partial}...)")
        def _delete_call():
            return svc.events().delete(
                calendarId=CALENDAR_ID,
                eventId=event_id
            ).execute()
        _retry(_delete_call, op_name="events.delete")
        
        logger.info(f"Deleted event from Google Calendar: {event_title}")
        return True
        
    except HttpError as e:
        if e.resp.status == 404:
            logger.warning(f"Event '{event_title}' not found (already deleted?)")
            return True  # Consider it successful if already gone
        elif e.resp.status == 403:
            logger.error(f"Permission denied deleting event '{event_title}'")
        else:
            logger.error(f"Google Calendar API error deleting event '{event_title}': {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting event '{event_title}': {e}")
        return False