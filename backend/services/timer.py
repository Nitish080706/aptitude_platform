"""
timer.py — server-side timer validation helpers.
"""
from datetime import datetime, timezone


def validate_elapsed(started_at: datetime, duration_seconds: int, buffer_secs: int = 5) -> bool:
    """
    Returns True if the submission is within the allowed window.
    started_at: UTC-aware datetime when the attempt started (stored in Firestore).
    duration_seconds: test duration in seconds.
    buffer_secs: grace period to account for network latency (default 5s).
    """
    now = datetime.now(timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    elapsed = (now - started_at).total_seconds()
    return elapsed <= (duration_seconds + buffer_secs)


def elapsed_seconds(started_at: datetime) -> float:
    """Returns how many seconds have passed since started_at."""
    now = datetime.now(timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return (now - started_at).total_seconds()
