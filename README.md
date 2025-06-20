# Calendar_Sync

## Overview
This project synchronizes events between a Microsoft Teams calendar (via ICS feed) and a Google Calendar. It performs a **two-way sync**:
- **Creates** events in Google Calendar that exist in Teams but not in Google Calendar.
- **Deletes** events from Google Calendar that no longer exist in Teams.
- **Handles cancellations**: If a Teams event starts with `Cancelado:`, the corresponding event is deleted from Google Calendar (and the cancellation event is not created).

## How It Works
1. **Fetch Teams events** for the next weeks using the ICS URL.
2. **Fetch Google Calendar events** for the same period.
3. **Handle 'Cancelado:' events**: For each Teams event starting with `Cancelado:`, find and delete the corresponding event in Google Calendar.
4. **Sync Teams → Google Calendar**: Create any Teams event not present in Google Calendar.
5. **Sync Google Calendar → Teams**: Delete any Google Calendar event not present in Teams.

This ensures that if an event changes date in Teams, the old event is deleted from Google Calendar and the new one is created, preventing duplicates.

## Setup
- Configure the following environment variables:
  - `TEAMS_ICS_URL`: ICS feed URL for your Teams calendar
  - `GOOGLE_CREDENTIALS`: Google service account credentials (JSON)
  - `GOOGLE_CALENDAR_ID`: Target Google Calendar ID
- Install dependencies:
  ```sh
  pip install -r requirements.txt
  ```
- Run the sync:
  ```sh
  python calendar_sync.py
  ```

## Automation
- The sync can be automated using GitHub Actions (see `.github/workflows/sync.yml`).

## Notes
- The sync window (number of days/weeks) is configurable in `src/config.py`.
- The script does not create events in Google Calendar for Teams events starting with `Cancelado:`; instead, it deletes the original event if found.
- The sync is **idempotent**: running it multiple times will not create duplicates.

## File Structure
- `calendar_sync.py`: Main sync script (two-way sync logic)
- `src/teams_functions.py`: Fetches and parses Teams events
- `src/google_calendar.py`: Google Calendar API integration
- `src/utils.py`: Utility functions (date parsing, etc.)
- `src/config.py`: Configuration

## Troubleshooting
- Ensure all environment variables are set.
- Check logs for details on created/deleted events and any errors.

---

**This README documents the new two-way sync logic and optimized handling of cancellations.**