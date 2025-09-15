"""
Microsoft Teams calendar functions.
"""

import requests
from datetime import datetime
from icalendar import Calendar as ICALCalendar
import recurring_ical_events

from src.logger import logger
from src.config import TEAMS_ICS_URL
from src.utils import get_sync_period

def get_teams_events():
    """
    Fetch events from Teams calendar for current and next week.
    
    Returns:
        tuple: (events_list, start_date, end_date) or (None, None, None) on error
        
    Raises:
        requests.RequestException: If ICS URL fetch fails
        Exception: If calendar parsing fails
    """
    try:
        logger.info("Fetching Teams calendar data...")
        
        if not TEAMS_ICS_URL:
            logger.error("TEAMS_ICS_URL environment variable is not set")
            return None, None, None
        
        # Add timeout and proper headers
        headers = {'User-Agent': 'Calendar-Sync/1.0'}
        resp = requests.get(TEAMS_ICS_URL, timeout=30, headers=headers)
        resp.raise_for_status()
        
        logger.info(f"Successfully fetched Teams calendar data ({len(resp.text)} chars)")
        
        # Parse calendar data
        ical = ICALCalendar.from_ical(resp.text)
        start, end = get_sync_period()
        
        logger.info(f"Parsing events for period: {start.date()} to {end.date()}")
        events = recurring_ical_events.of(ical).between(start, end)
        
        out = []
        for e in events:
            try:
                s = e.get('DTSTART').dt
                f = e.get('DTEND').dt
                
                if not isinstance(s, datetime): 
                    s = datetime.combine(s, datetime.min.time())
                if not isinstance(f, datetime): 
                    f = datetime.combine(f, datetime.min.time())
                    
                event_title = str(e.get('SUMMARY', 'Untitled Event'))
                
                out.append({
                    'titulo': event_title,
                    'inicio': s.replace(tzinfo=None),
                    'fim': f.replace(tzinfo=None)
                })
            except Exception as e_err:
                logger.warning(f"Error processing individual event: {e_err}")
                continue
        
        logger.info(f"Successfully processed {len(out)} Teams events")
        return out, start, end
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Teams calendar: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"HTTP Status: {e.response.status_code}")
        return None, None, None
    except Exception as e:
        logger.error(f"Error parsing Teams calendar: {e}")
        return None, None, None