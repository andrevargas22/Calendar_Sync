"""
Configuration for the calendar sync application.
"""

import os
import hashlib
from typing import Optional

def _get_bool(env_name: str, default: bool = False) -> bool:
	"""Get boolean value from environment variable."""
	val = os.environ.get(env_name)
	if val is None:
		return default
	return val.strip().lower() in {"1", "true", "yes", "y", "on"}

def _get_int(env_name: str, default: int, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
	"""Get integer value from environment variable with validation."""
	val = os.environ.get(env_name)
	if val is None:
		return default
	try:
		num = int(val.strip())
		if min_val is not None and num < min_val:
			raise ValueError(f"{env_name} must be >= {min_val}, got {num}")
		if max_val is not None and num > max_val:
			raise ValueError(f"{env_name} must be <= {max_val}, got {num}")
		return num
	except ValueError as e:
		raise ValueError(f"Invalid integer for {env_name}: {val}") from e

# Base configuration
TEAMS_ICS_URL = os.environ.get('TEAMS_ICS_URL')
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
CALENDAR_ID = os.environ.get('GOOGLE_CALENDAR_ID')
GOOGLE_SERVICE_ACCOUNT_KEY = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
TIMEZONE = 'America/Sao_Paulo'

# Behavior / security related
CANCEL_PREFIX = os.environ.get('CANCEL_PREFIX', 'Cancelado:')
LOG_MASK_TITLES = _get_bool('LOG_MASK_TITLES', True)

def mask_title(title: str) -> str:
	"""Return masked or original title based on LOG_MASK_TITLES flag."""
	if not LOG_MASK_TITLES:
		return title
	if not title:
		return title
	h = hashlib.sha256(title.encode('utf-8')).hexdigest()[:12]
	return f"EVENT[{h}]"

# Time range configuration (with validation)
START_HOUR = _get_int('START_HOUR', 7, min_val=0, max_val=23)    # Starting hour for period
END_HOUR = _get_int('END_HOUR', 18, min_val=0, max_val=23)       # Ending hour for period
DAYS_RANGE = _get_int('DAYS_RANGE', 11, min_val=1, max_val=365)  # Number of days to sync