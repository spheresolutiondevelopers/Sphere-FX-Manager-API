"""Date and time utilities."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Union
import re


def utc_now() -> datetime:
    """Return current UTC datetime with timezone awareness."""
    return datetime.now(timezone.utc)


def utc_from_timestamp(ts: Union[int, float]) -> datetime:
    """Convert a timestamp to UTC datetime."""
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Parse an ISO 8601 datetime string to UTC datetime."""
    try:
        # Handles both with and without timezone
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def format_iso_datetime(dt: datetime) -> str:
    """Format a datetime as ISO 8601 with UTC timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def to_utc(dt: datetime) -> datetime:
    """Convert a datetime to UTC if it's timezone-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def truncate_to_hour(dt: datetime) -> datetime:
    """Truncate a datetime to the start of the hour."""
    return dt.replace(minute=0, second=0, microsecond=0)


def truncate_to_day(dt: datetime) -> datetime:
    """Truncate a datetime to the start of the day."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def days_ago(days: int) -> datetime:
    """Return a UTC datetime `days` ago from now."""
    return utc_now() - timedelta(days=days)


def hours_ago(hours: int) -> datetime:
    """Return a UTC datetime `hours` ago from now."""
    return utc_now() - timedelta(hours=hours)


def minutes_ago(minutes: int) -> datetime:
    """Return a UTC datetime `minutes` ago from now."""
    return utc_now() - timedelta(minutes=minutes)


def seconds_ago(seconds: int) -> datetime:
    """Return a UTC datetime `seconds` ago from now."""
    return utc_now() - timedelta(seconds=seconds)


def time_ago(dt: datetime) -> str:
    """
    Return a human-readable time ago string (e.g., "2 hours ago").
    """
    now = utc_now()
    diff = now - dt

    if diff < timedelta(minutes=1):
        return "just now"
    if diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    if diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    if diff < timedelta(days=30):
        days = diff.days
        return f"{days} day{'s' if days > 1 else ''} ago"
    if diff < timedelta(days=365):
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    years = diff.days // 365
    return f"{years} year{'s' if years > 1 else ''} ago"


def validate_date_range(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    max_range_days: int = 365,
) -> bool:
    """
    Validate a date range: start <= end, and not exceeding max_range_days.
    Returns True if valid, False otherwise.
    """
    if start_date and end_date:
        if start_date > end_date:
            return False
        diff = end_date - start_date
        if diff.total_seconds() > max_range_days * 86400:
            return False
    return True