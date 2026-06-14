"""Timestamp and temporal helpers for the Alexa Thinks Ahead system."""

from datetime import datetime, timezone

from src.utils.constants import SEASONS


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def get_current_season() -> str:
    """Determine current Indian season from month.

    Seasons: summer (Mar-Jun), monsoon (Jul-Sep),
    autumn (Oct-Nov), winter (Dec-Feb).
    """
    month = get_current_timestamp().month
    for season, months in SEASONS.items():
        if month in months:
            return season
    return "summer"  # fallback


def time_since_seconds(timestamp: datetime) -> float:
    """Calculate seconds elapsed since a given timestamp."""
    now = get_current_timestamp()
    delta = now - timestamp
    return max(0.0, delta.total_seconds())


def is_within_hours(timestamp: datetime, hours: int) -> bool:
    """Check if a timestamp is within the last N hours."""
    elapsed = time_since_seconds(timestamp)
    return elapsed <= hours * 3600


def format_iso(timestamp: datetime) -> str:
    """Format a datetime as ISO 8601 string."""
    return timestamp.isoformat()


def parse_iso(timestamp_str: str) -> datetime:
    """Parse an ISO 8601 string to datetime."""
    from dateutil.parser import isoparse

    return isoparse(timestamp_str)
