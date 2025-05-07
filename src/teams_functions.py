"""Microsoft Teams calendar functions."""
import requests
from datetime import datetime, timedelta
from icalendar import Calendar as ICALCalendar
import recurring_ical_events

from src.logger import logger
from src.config import TEAMS_ICS_URL
from src.utils import get_sync_period

def get_teams_events():
    """
    Fetch events from Teams calendar for current and next week.
    
    Returns:
        tuple: (events_list, start_date, end_date)
    """
    resp = requests.get(TEAMS_ICS_URL)
    resp.raise_for_status()
    ical = ICALCalendar.from_ical(resp.text)
    
    start, end = get_sync_period()
    events = recurring_ical_events.of(ical).between(start, end)
    out = []
    
    for e in events:
        s = e.get('DTSTART').dt
        f = e.get('DTEND').dt
        if not isinstance(s, datetime): 
            s = datetime.combine(s, datetime.min.time())
        if not isinstance(f, datetime): 
            f = datetime.combine(f, datetime.min.time())
        out.append({
            'titulo': str(e.get('SUMMARY')),
            'inicio': s.replace(tzinfo=None),
            'fim': f.replace(tzinfo=None)
        })
    
    return out, start, end