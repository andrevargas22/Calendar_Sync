"""GCP and cache functions for the calendar sync application."""
import csv
import io
import json
from google.oauth2 import service_account
from google.cloud import storage
from src.logger import logger
from src.config import GCS_BUCKET, GCS_BLOB, CREDENTIALS_JSON

def get_gcp_credentials():
    """
    Get GCP credentials from environment variable.
    
    Returns:
        Service account credentials object
    """
    if not CREDENTIALS_JSON:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not found")
    credentials_info = json.loads(CREDENTIALS_JSON)
    return service_account.Credentials.from_service_account_info(credentials_info)

def download_cache_from_gcs():
    """
    Download CSV cache from GCS and return as set of tuples.
    
    Returns:
        Set of tuples containing event data (titulo, inicio, fim)
    """
    credentials = get_gcp_credentials()
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB)
    
    if not blob.exists():
        # Only log at debug level to reduce verbosity
        logger.debug(f"No cache file found at {GCS_BUCKET}/{GCS_BLOB}")
        return set()
        
    content = blob.download_as_text()
    reader = csv.DictReader(io.StringIO(content))
    cache = set()
    
    for row in reader:
        cache.add((row['titulo'], row['inicio'], row['fim']))
    
    # This is sufficient - we don't need to log "downloaded from GCS"
    logger.debug(f"Cache loaded: {len(cache)} events")
    return cache

def upload_cache_to_gcs(cache_set):
    """
    Upload the cache set as CSV to GCS.
    
    Args:
        cache_set: Set of tuples containing event data
    """
    credentials = get_gcp_credentials()
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB)
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['titulo', 'inicio', 'fim'])
    writer.writeheader()
    
    for titulo, inicio, fim in cache_set:
        writer.writerow({'titulo': titulo, 'inicio': inicio, 'fim': fim})
    
    blob.upload_from_string(output.getvalue(), content_type='text/csv')
    logger.debug(f"Cache saved: {len(cache_set)} events")

def load_event_cache():
    """
    Load cached events from GCS CSV file.
    
    Returns:
        Set of cached events
    """
    return download_cache_from_gcs()

def append_events_to_cache(new_events, cached_set):
    """
    Append new events to cache if not already present.
    
    Args:
        new_events: List of new events to potentially add
        cached_set: Current set of cached events
        
    Returns:
        List of events that were newly added
    """
    added = []
    
    for event in new_events:
        key = (
            event['titulo'],
            event['inicio'].isoformat(),
            event['fim'].isoformat()
        )
        
        if key not in cached_set:
            cached_set.add(key)
            added.append(event)
    
    if added:
        upload_cache_to_gcs(cached_set)
    
    return added

def clean_old_events_from_cache(cached_set, current_window_start):
    """
    Remove events from cache that are from before the current window.
    
    Args:
        cached_set: Set of cached events as (title, start, end) tuples
        current_window_start: Datetime object representing the start of current window
        
    Returns:
        Set of cached events with old events removed
    """
    from src.utils import parse_datetime
    
    current_count = len(cached_set)
    filtered_set = set()
    
    for titulo, inicio, fim in cached_set:
        event_start = parse_datetime(inicio)
        
        # Keep events that start on or after the window start
        if event_start >= current_window_start:
            filtered_set.add((titulo, inicio, fim))
    
    removed_count = current_count - len(filtered_set)
    
    if removed_count > 0:
        logger.info(f"Removed {removed_count} old events from cache")
        upload_cache_to_gcs(filtered_set)
    
    return filtered_set