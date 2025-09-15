"""
Configuration for the calendar sync application.
"""

import os

# Base configuration
TEAMS_ICS_URL = os.environ['TEAMS_ICS_URL']
CACHE_FILE = 'events_cache.csv'
GCS_BUCKET = "calendar_sync"
GCS_BLOB = "events_cache.csv"
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS')
TIMEZONE = 'America/Sao_Paulo'

# Time range configuration
DAYS_BEFORE = 30  # For searching canceled events
DAYS_AFTER = 30   # For searching canceled events
START_HOUR = 7    # Starting hour for period
END_HOUR = 18     # Ending hour for period
DAYS_RANGE = 11   # Number of days to sync