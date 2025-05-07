"""
Calendar Sync - Synchronizes Microsoft Teams calendar with Google Calendar.
"""
import os
from datetime import datetime

# Import modules
from src.logger import logger
from src.config import CREDENTIALS_JSON, CALENDAR_ID
from src.teams_functions import get_teams_events
from src.gcp_functions import load_event_cache, append_events_to_cache
from src.google_calendar import (
    get_calendar_service, 
    get_google_events, 
    criar_evento_google, 
    buscar_e_deletar_cancelados
)
from src.utils import parse_datetime

def main():
    """Main synchronization process."""
    logger.info("Calendar Sync Process Starting")
        
    # 1. Fetch Teams events
    logger.info("\n1. Fetching Teams events for current and next week...")
    current_events, start, end = get_teams_events()
    current_events_sorted = sorted(current_events, key=lambda e: e['inicio'])
    logger.info(f"Found {len(current_events)} events")

if __name__ == '__main__':
    main()