"""
DateTime helper functions for timezone-aware operations
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """
    Get current UTC time as timezone-aware datetime

    Replaces deprecated datetime.utcnow() with datetime.now(timezone.utc)

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.now(UTC)


def utc_timestamp() -> str:
    """
    Get current UTC timestamp as ISO format string

    Returns:
        ISO format timestamp string
    """
    return utcnow().isoformat()
