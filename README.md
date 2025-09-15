# Calendar_Sync

## Overview
Synchronizes Microsoft Teams calendar events (via ICS) with Google Calendar, ensuring Google Calendar always reflects what's in Teams.

## How it works
- Fetches events from both Teams and Google Calendar for the configured period.
- Removes from Google any event that no longer exists in Teams.
- Creates in Google any new event from Teams.
- The script is idempotent: running it multiple times doesn't create duplicates.

## Structure
- `calendar_sync.py`: Main script
- `src/`: Helper functions and API integrations

---
Personal project for personal use.