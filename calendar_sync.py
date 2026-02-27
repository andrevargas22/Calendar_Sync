"""
Calendar Sync - Synchronizes Microsoft Teams calendar with Google Calendar.
"""

import sys
import pytz
from datetime import datetime
from collections import defaultdict

from src.logger import logger
from src.teams_functions import get_teams_events
from src.google_calendar import (
    get_calendar_service,
    get_google_events,
    create_google_event,
    delete_google_event_by_id
)
from src.utils import parse_datetime
from src.config import (
    TEAMS_ICS_URL,
    GOOGLE_SERVICE_ACCOUNT_KEY,
    CALENDAR_ID,
    CANCEL_PREFIX,
    LOG_MASK_TITLES,
)

# Set timezone
LOCAL_TZ = pytz.timezone('America/Sao_Paulo')

def to_local(dt: datetime) -> datetime:
    """Convert datetime to local timezone."""
    if dt.tzinfo is None:
        return LOCAL_TZ.localize(dt)
    return dt.astimezone(LOCAL_TZ)

def normalize_event(event: dict, source: str) -> tuple[str, str, str]:
    """Normalize event to comparable format."""
    # Handle empty or None titles safely
    title = (event.get('title') or '').strip()
    start_raw = parse_datetime(event['start'])
    end_raw = parse_datetime(event['end'])
    if source == 'google':
        start = start_raw.astimezone(LOCAL_TZ).replace(tzinfo=None, microsecond=0)
        end = end_raw.astimezone(LOCAL_TZ).replace(tzinfo=None, microsecond=0)
    else:
        start = to_local(start_raw).replace(tzinfo=None, microsecond=0)
        end = to_local(end_raw).replace(tzinfo=None, microsecond=0)
    logger.debug(f"NORMALIZE({source}): processing event - raw_start={start_raw} raw_end={end_raw} norm_start={start} norm_end={end}")
    return (title, start.isoformat(sep='T'), end.isoformat(sep='T'))

def main() -> None:
    """Main synchronization function."""
    logger.info("Calendar Sync Process Starting")

    # 0. Validate configuration
    logger.info("0. Validating configuration...")
    required_configs = {
        "TEAMS_ICS_URL": TEAMS_ICS_URL,
        "GOOGLE_SERVICE_ACCOUNT_KEY": GOOGLE_SERVICE_ACCOUNT_KEY,
        "GOOGLE_CALENDAR_ID": CALENDAR_ID,
    }

    missing_configs = [
        key for key, value in required_configs.items() if not value
    ]

    if missing_configs:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_configs)}"
        )
        sys.exit(1)

    logger.info("Configuration validated successfully.")

    # 1. Fetch Teams events
    logger.info("1. Fetching Teams events for sync window...")
    teams_events, start, end = get_teams_events()
    if teams_events is None:
        logger.error("Halting execution due to error fetching Teams events.")
        sys.exit(1)
    logger.info(f"Found {len(teams_events)} events from Teams")

    # 2. Fetch Google Calendar events
    logger.info("2. Fetching Google Calendar events for sync window...")
    svc = get_calendar_service()
    google_events = get_google_events(svc, start, end)
    logger.info(f"Found {len(google_events)} events in Google Calendar")

    # 3. Build lookup dicts for fast existence checks
    # Using defaultdict(list) to handle duplicate events (same title+time)
    teams_dict = defaultdict(list)
    cancelado_events = []
    for ev in teams_events:
        title = ev.get('title') or ''
        if title.startswith(CANCEL_PREFIX):
            cancelado_events.append(ev)
        else:
            teams_dict[normalize_event(ev, 'teams')].append(ev)

    google_dict = defaultdict(list)
    for ev in google_events:
        google_dict[normalize_event(ev, 'google')].append(ev)

    # Counters for summary (privacy friendly)
    created_count = 0
    deleted_count = 0
    canceled_deleted_count = 0
    missing_cancel_matches = 0

    # 4. Handle canceled events (no detailed timestamps in logs)
    logger.info("4. Handling canceled events from Teams (privacy masked)...")
    for cancel_ev in cancelado_events:
        original_title = cancel_ev['title'].replace(CANCEL_PREFIX, "").strip()
        original_start = to_local(parse_datetime(cancel_ev['start'])).replace(tzinfo=None, microsecond=0)
        original_end = to_local(parse_datetime(cancel_ev['end'])).replace(tzinfo=None, microsecond=0)
        key = (original_title, original_start.isoformat(sep='T'), original_end.isoformat(sep='T'))
        g_events_list = google_dict.get(key, [])
        if g_events_list:
            # Delete all matching events for this canceled event
            for g_ev in g_events_list:
                delete_google_event_by_id(
                    svc,
                    g_ev.get('id', None),
                    g_ev['title'],
                    g_ev['start'],
                    g_ev['end']
                )
                canceled_deleted_count += 1
        else:
            missing_cancel_matches += 1

    if canceled_deleted_count:
        logger.info(f"Canceled events removed: {canceled_deleted_count}")
    if missing_cancel_matches:
        logger.info(f"Canceled events without Google match: {missing_cancel_matches}")

    # 5. Teams → Google Calendar: create missing events or duplicates
    logger.info("5. Creating missing events in Google Calendar (privacy masked)...")
    for key, teams_events_list in teams_dict.items():
        google_events_list = google_dict.get(key, [])
        teams_count = len(teams_events_list)
        google_count = len(google_events_list)
        
        # If Teams has more events than Google, create the difference
        if teams_count > google_count:
            events_to_create = teams_count - google_count
            # Use first event as template for all duplicates
            template_ev = teams_events_list[0]
            for _ in range(events_to_create):
                create_google_event(svc, {
                    'title': template_ev['title'],
                    'start': to_local(parse_datetime(template_ev['start'])).replace(tzinfo=None, microsecond=0).isoformat(sep='T'),
                    'end': to_local(parse_datetime(template_ev['end'])).replace(tzinfo=None, microsecond=0).isoformat(sep='T')
                })
                created_count += 1

    if created_count == 0:
        logger.info("No new events created.")
    else:
        logger.info(f"Events created: {created_count}")

    # 6. Google Calendar → Teams: delete orphan events or excess duplicates
    logger.info("6. Deleting orphan Google events (privacy masked)...")
    for key, google_events_list in google_dict.items():
        teams_events_list = teams_dict.get(key, [])
        google_count = len(google_events_list)
        teams_count = len(teams_events_list)
        
        # If Google has more events than Teams, delete the difference
        if google_count > teams_count:
            events_to_delete = google_count - teams_count
            # Delete the excess events (doesn't matter which ones)
            for i in range(events_to_delete):
                g_ev = google_events_list[i]
                delete_google_event_by_id(
                    svc,
                    g_ev.get('id', None),
                    g_ev['title'],
                    g_ev['start'],
                    g_ev['end']
                )
                deleted_count += 1

    if deleted_count == 0:
        logger.info("No orphan events deleted.")
    else:
        logger.info(f"Orphan events deleted: {deleted_count}")

    # Final summary
    logger.info("Sync summary (privacy masked): "
                f"created={created_count} deleted={deleted_count} canceled_removed={canceled_deleted_count} "
                f"cancel_no_match={missing_cancel_matches}")
    logger.info("Calendar Sync Process Completed")

if __name__ == '__main__':
    main()