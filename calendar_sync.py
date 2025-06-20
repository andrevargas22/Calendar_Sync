"""
Calendar Sync - Synchronizes Microsoft Teams calendar with Google Calendar (two-way sync).
"""
import os
from datetime import datetime, timedelta

from src.logger import logger
from src.teams_functions import get_teams_events
from src.google_calendar import (
    get_calendar_service,
    get_google_events,
    criar_evento_google,
    remover_evento_google_by_id
)
from src.utils import parse_datetime

def normalize_event(event):
    """
    Normalize event dict to a tuple (title, start, end) for comparison.
    Dates are converted to ISO string (no microseconds, no tzinfo).
    """
    return (
        event['titulo'],
        parse_datetime(event['inicio']).isoformat(sep='T'),
        parse_datetime(event['fim']).isoformat(sep='T')
    )

def main():
    logger.info("Calendar Sync Process Starting (two-way sync)")

    # 1. Fetch Teams events
    logger.info("1. Fetching Teams events for sync window...")
    teams_events, start, end = get_teams_events()
    logger.info(f"Found {len(teams_events)} events from Teams")

    # 2. Fetch Google Calendar events
    logger.info("2. Fetching Google Calendar events for sync window...")
    svc = get_calendar_service()
    google_events = get_google_events(svc, start, end)
    logger.info(f"Found {len(google_events)} events in Google Calendar")

    # 3. Build normalized sets for comparison
    teams_set = set()
    cancelado_events = []
    for ev in teams_events:
        if ev['titulo'].startswith("Cancelado:"):
            cancelado_events.append(ev)
        else:
            teams_set.add(normalize_event(ev))

    google_set = set(normalize_event(ev) for ev in google_events)

    # 4. Handle 'Cancelado:' events (delete originals from Google Calendar)
    logger.info("3. Handling 'Cancelado:' events from Teams...")
    for cancel_ev in cancelado_events:
        # Find the original event title (remove 'Cancelado: ')
        original_title = cancel_ev['titulo'].replace("Cancelado:", "").strip()
        original_start = parse_datetime(cancel_ev['inicio'])
        original_end = parse_datetime(cancel_ev['fim'])
        # Try to find a matching event in Google Calendar
        for g_ev in google_events:
            if (g_ev['titulo'] == original_title and
                parse_datetime(g_ev['inicio']) == original_start and
                parse_datetime(g_ev['fim']) == original_end):
                # Delete the event by ID
                remover_evento_google_by_id(
                    svc,
                    g_ev.get('id', None),
                    g_ev['titulo'],
                    g_ev['inicio'],
                    g_ev['fim']
                )
                logger.info(f"Deleted event due to 'Cancelado:': {original_title} ({original_start} - {original_end})")
                break
        else:
            logger.info(f"No matching event found in Google Calendar for 'Cancelado:' {original_title}")

    # 5. Teams → Google Calendar: create missing events
    logger.info("4. Creating events missing in Google Calendar...")
    to_create = teams_set - google_set
    for titulo, inicio, fim in to_create:
        # Double-check: do not create 'Cancelado:' events
        if titulo.startswith("Cancelado:"):
            continue
        ev = {
            'titulo': titulo,
            'inicio': inicio,
            'fim': fim
        }
        criar_evento_google(svc, ev)
        logger.info(f"Created event in Google Calendar: {titulo} ({inicio} - {fim})")
    if not to_create:
        logger.info("No new events to create in Google Calendar.")

    # 6. Google Calendar → Teams: delete events not in Teams
    logger.info("5. Deleting events from Google Calendar not present in Teams...")
    to_delete = google_set - teams_set
    for titulo, inicio, fim in to_delete:
        # Find the event in Google Calendar to get its ID
        for g_ev in google_events:
            if (g_ev['titulo'] == titulo and
                parse_datetime(g_ev['inicio']).isoformat(sep='T') == inicio and
                parse_datetime(g_ev['fim']).isoformat(sep='T') == fim):
                remover_evento_google_by_id(
                    svc,
                    g_ev.get('id', None),
                    g_ev['titulo'],
                    g_ev['inicio'],
                    g_ev['fim']
                )
                logger.info(f"Deleted event from Google Calendar: {titulo} ({inicio} - {fim})")
                break
    if not to_delete:
        logger.info("No events to delete from Google Calendar.")

    logger.info("Calendar Sync Process Completed (two-way sync)")

if __name__ == '__main__':
    main()