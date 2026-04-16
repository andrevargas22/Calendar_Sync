"""
Configuration for the calendar sync application.
"""

import os
import hashlib
from pathlib import Path

# Load .env file if present (local development)
_env_path = Path(__file__).resolve().parent.parent / '.env'
if _env_path.is_file():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _, _val = _line.partition('=')
                os.environ.setdefault(_key.strip(), _val.strip())

def _get_bool(env_name: str, default: bool = False) -> bool:
	val = os.environ.get(env_name)
	if val is None:
		return default
	return val.strip().lower() in {"1", "true", "yes", "y", "on"}

# Base configuration
TEAMS_ICS_URL = os.environ.get('TEAMS_ICS_URL')
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
GOOGLE_SERVICE_ACCOUNT_KEY = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
TIMEZONE = 'America/Sao_Paulo'

# Behavior / security related
CANCEL_PREFIX = os.environ.get('CANCEL_PREFIX', 'Cancelado:')
CANCEL_PREFIXES = tuple(
	p.strip() for p in os.environ.get(
		'CANCEL_PREFIXES',
		f"{CANCEL_PREFIX},Cancelado:,Canceled event:,Cancelled event:,Canceled:,Cancelled:"
	).split(',') if p.strip()
)
LOG_MASK_TITLES = _get_bool('LOG_MASK_TITLES', True)

def mask_title(title: str) -> str:
	"""Return masked or original title based on LOG_MASK_TITLES flag."""
	if not LOG_MASK_TITLES:
		return title
	if not title:
		return title
	h = hashlib.sha256(title.encode('utf-8')).hexdigest()[:12]
	return f"EVENT[{h}]"

# Time range configuration
START_HOUR = 7    # Starting hour for period
END_HOUR = 18     # Ending hour for period
DAYS_RANGE = 11   # Number of days to sync
LOOKBACK_DAYS = int(os.environ.get('LOOKBACK_DAYS', 30))  # Days to look back for stale canceled events