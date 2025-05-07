# src/config.py
import os
import json

# Configuration constants
TEAMS_ICS_URL = os.environ['TEAMS_ICS_URL']
CACHE_FILE = 'events_cache.csv'
GCS_BUCKET = "calendar_sync"
GCS_BLOB = "events_cache.csv"
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS')