from google.cloud import storage
import csv
import os

# Set GOOGLE_APPLICATION_CREDENTIALS env var or authenticate in your environment
CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS')
if CREDENTIALS_JSON:
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_JSON
    
BUCKET_NAME = "calendar_sync"
BLOB_NAME = "events_cache.csv"

def read_csv_from_gcs(bucket_name, blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    content = blob.download_as_text()
    reader = csv.reader(content.splitlines())
    for row in reader:
        print(row)

if __name__ == "__main__":
    read_csv_from_gcs(BUCKET_NAME, BLOB_NAME)
