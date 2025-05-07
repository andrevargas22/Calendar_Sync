import requests
from datetime import datetime, timedelta
from icalendar import Calendar as ICALCalendar
import recurring_ical_events

# Import the logger
from src.logger import logger

def get_teams_events(teams_ics_url):
    """Fetch events from Teams calendar for current and next week"""
    resp = requests.get(teams_ics_url)
    resp.raise_for_status()
    ical = ICALCalendar.from_ical(resp.text)
    
    hoje = datetime.now()
    seg_atual = hoje - timedelta(days=hoje.weekday())
    
    # Define período para duas semanas
    start = seg_atual.replace(hour=7, minute=0, second=0, microsecond=0)
    end = (seg_atual + timedelta(days=11)).replace(hour=18, minute=0, second=0, microsecond=0)
    
    logger.info(f"📅 From: {start.strftime('%d/%m')} | To: {end.strftime('%d/%m')}")
    events = recurring_ical_events.of(ical).between(start, end)
    out = []
    
    for e in events:
        s = e.get('DTSTART').dt
        f = e.get('DTEND').dt
        if not isinstance(s, datetime): s = datetime.combine(s, datetime.min.time())
        if not isinstance(f, datetime): f = datetime.combine(f, datetime.min.time())
        out.append({
            'titulo': str(e.get('SUMMARY')),
            'inicio': s.replace(tzinfo=None),
            'fim': f.replace(tzinfo=None)
        })
    
    return out, start, end