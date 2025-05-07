# ——————————— IMPORTS ———————————
import os, json, requests, csv
from datetime import datetime, timedelta
from icalendar import Calendar as ICALCalendar
import recurring_ical_events
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import storage
import pandas as pd
import io

from src.logger import logger
from src.teams_functions import get_teams_events
from src.config import TEAMS_ICS_URL, CACHE_FILE, GCS_BUCKET, GCS_BLOB

# ————————— MAIN —————————
if __name__ == '__main__':
    
    logger.info("Starting Calendar Sync")
    logger.info("1. Fetching Teams events for current and next week...")
    
    current_events, start, end = get_teams_events(TEAMS_ICS_URL)
    current_events_sorted = sorted(current_events, key=lambda e: e['inicio'])

    logger.info(f"Found {len(current_events)} events")
    


