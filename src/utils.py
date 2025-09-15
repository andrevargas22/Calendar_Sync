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
        
        dtstr = dtstr.replace('T', ' ')
        
        # Handle timezone information
        if '+' in dtstr:
            dtstr = dtstr.split('+')[0]
        elif '-' in dtstr[11:]:  
            dtstr = dtstr[:19]  
            
        # Parse the datetime
        dt = datetime.fromisoformat(dtstr.strip())
    else:
        dt = dtstr
        
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    
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
    
    logger.info(f"Sync period: {start.strftime('%d/%m')} - {end.strftime('%d/%m')}")
    return start, end