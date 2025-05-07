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
        logger.info(f"No cache file found at {GCS_BUCKET}/{GCS_BLOB}")
        return set()
        
    content = blob.download_as_text()
    reader = csv.DictReader(io.StringIO(content))
    cache = set()
    
    for row in reader:
        cache.add((row['titulo'], row['inicio'], row['fim']))
    
    logger.info(f"Downloaded cache with {len(cache)} events from GCS")
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
    logger.info(f"Uploaded cache with {len(cache_set)} events to GCS")

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
        logger.info(f"Adding {len(added)} new events to cache")
        upload_cache_to_gcs(cached_set)
    else:
        logger.info("No new events to add to cache")
        
    return added