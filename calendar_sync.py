"""
Calendar Sync - Synchronizes Microsoft Teams calendar with Google Calendar.
"""
import os
from datetime import datetime, timedelta

# Import modules
from src.logger import logger
from src.config import CREDENTIALS_JSON, CALENDAR_ID
from src.teams_functions import get_teams_events
from src.gcp_functions import load_event_cache, append_events_to_cache, clean_old_events_from_cache
from src.google_calendar import (
    get_calendar_service, 
    get_google_events, 
    criar_evento_google, 
    buscar_e_deletar_cancelados
)
from src.utils import parse_datetime, compare_events_with_timezone

def main():
    """Main synchronization process."""
    logger.info("Calendar Sync Process Starting")
        
    # 1. Fetch Teams events
    logger.info("1. Fetching Teams events for current and next week...")
    current_events, start, end = get_teams_events()
    current_events_sorted = sorted(current_events, key=lambda e: e['inicio'])
    logger.info(f"Found {len(current_events)} events")
    
    # 2. Update events cache
    logger.info("2. Updating cache...")
    cached_set = load_event_cache()
    logger.info(f"Loaded {len(cached_set)} events from cache")
    
    # Clean old events from cache
    cached_set = clean_old_events_from_cache(cached_set, start)
    
    # Add new events to cache
    new_events = append_events_to_cache(current_events_sorted, cached_set)
    if new_events:
        logger.info(f"Added {len(new_events)} new events to cache (total: {len(cached_set)})")
    else:
        logger.info(f"No new events to add (cache: {len(cached_set)} events)")
        
    # 3. Fetch Google Calendar events
    logger.info("3. Fetching Google Calendar events...")
    svc = get_calendar_service()
    google_events = get_google_events(svc, start, end)
    logger.info(f"Found {len(google_events)} events in Google Calendar")
    
    # 4. Identify and create missing events
    logger.info("4. Identifying events to create in Google Calendar...")
    events_to_create = compare_events_with_timezone(cached_set, google_events)
    
    if events_to_create:
        logger.info(f"Creating {len(events_to_create)} events in Google Calendar...")
        created_count = 0
        for titulo, inicio, fim in events_to_create:
            ev = {
                'titulo': titulo,
                'inicio': inicio if 'T' in inicio else inicio.replace(' ', 'T'),
                'fim': fim if 'T' in fim else fim.replace(' ', 'T')
            }
            criar_evento_google(svc, ev)
            created_count += 1
            
            # Log progress for larger batches
            if created_count % 5 == 0:
                logger.info(f"Created {created_count}/{len(events_to_create)} events...")
                
        logger.info(f"Successfully created {created_count} events in Google Calendar")
    else:
        logger.info("All cached events are already in Google Calendar")
        
    # 5. Handle canceled events
    logger.info("5. Checking for 'Cancelado:' events...")
    buscar_e_deletar_cancelados(svc)
    
    logger.info("Calendar Sync Process Completed")

if __name__ == '__main__':
    main()