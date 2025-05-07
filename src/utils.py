"""Utility functions for the calendar sync application."""
from datetime import datetime, timedelta
from src.logger import logger

def parse_datetime(dtstr):
    """
    Improved parsing of datetime strings to ensure consistent format.
    
    Args:
        dtstr: Datetime string or datetime object
    
    Returns:
        Datetime object with normalized format (no timezone, no microseconds)
    """
    # Remove any timezone information and standardize format
    if isinstance(dtstr, str):
        # Replace T with space for consistent formatting
        dtstr = dtstr.replace('T', ' ')
        
        # Handle timezone information
        if '+' in dtstr:
            dtstr = dtstr.split('+')[0]
        elif '-' in dtstr[11:]:  # Only check for timezone in the time part
            dtstr = dtstr[:19]  # Keep only YYYY-MM-DD HH:MM:SS part
            
        # Parse the datetime
        dt = datetime.fromisoformat(dtstr.strip())
    else:
        # If already a datetime object
        dt = dtstr
        
    # Ensure no timezone info and no microseconds
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    
    # Remove microseconds to ensure consistent comparison
    return dt.replace(microsecond=0)

def get_sync_period():
    """
    Calculate the current sync period (current week + a few days).
    
    Returns:
        tuple: (start_date, end_date) for the sync period
    """
    from src.config import START_HOUR, END_HOUR, DAYS_RANGE
    
    hoje = datetime.now()
    seg_atual = hoje - timedelta(days=hoje.weekday())
    
    # Define period for two weeks
    start = seg_atual.replace(hour=START_HOUR, minute=0, second=0, microsecond=0)
    end = (seg_atual + timedelta(days=DAYS_RANGE)).replace(hour=END_HOUR, minute=0, second=0, microsecond=0)
    
    logger.info(f"📅 Sync period: {start.strftime('%d/%m')} - {end.strftime('%d/%m')}")
    return start, end

def compare_events_with_timezone(cached_set, google_events, timezone_offset=3):
    """
    Compare cached events with Google Calendar events, accounting for timezone differences.
    
    Args:
        cached_set: Set of cached events as (title, start, end) tuples
        google_events: List of Google Calendar events
        timezone_offset: Timezone difference in hours (3 for Brazil/UTC-3)
        
    Returns:
        List of events to create as (title, start, end) tuples
    """
    # Create a more effective lookup structure by title
    google_events_by_title = {}
    for event in google_events:
        title = event['titulo']
        if title not in google_events_by_title:
            google_events_by_title[title] = []
        
        # Add the start and end times - both raw and normalized
        start_time = parse_datetime(event['inicio'])
        end_time = parse_datetime(event['fim'])
        
        google_events_by_title[title].append({
            'start': start_time,
            'end': end_time,
            'start_str': start_time.strftime('%Y-%m-%d %H:%M'),
            'end_str': end_time.strftime('%Y-%m-%d %H:%M')
        })
    
    # Find events in cache but not in Google Calendar, accounting for timezone
    events_to_create = []
    
    for titulo, inicio, fim in cached_set:
        # Parse the datetime objects from cache strings
        cache_start = parse_datetime(inicio)
        cache_end = parse_datetime(fim)
        
        # Check if this event exists in Google Calendar
        event_exists = False
        
        if titulo in google_events_by_title:
            # Try exact match first
            for gcal_event in google_events_by_title[titulo]:
                if (cache_start.strftime('%Y-%m-%d %H:%M') == gcal_event['start_str'] and
                    cache_end.strftime('%Y-%m-%d %H:%M') == gcal_event['end_str']):
                    event_exists = True
                    break
            
            # If not found, try with timezone adjustment
            if not event_exists:
                # Add offset hours to cache times (UTC to local time)
                adjusted_start = cache_start + timedelta(hours=timezone_offset)
                adjusted_end = cache_end + timedelta(hours=timezone_offset)
                
                adjusted_start_str = adjusted_start.strftime('%Y-%m-%d %H:%M')
                adjusted_end_str = adjusted_end.strftime('%Y-%m-%d %H:%M')
                
                for gcal_event in google_events_by_title[titulo]:
                    if (adjusted_start_str == gcal_event['start_str'] and
                        adjusted_end_str == gcal_event['end_str']):
                        event_exists = True
                        break
        
        if not event_exists:
            events_to_create.append((titulo, inicio, fim))
    
    return events_to_create