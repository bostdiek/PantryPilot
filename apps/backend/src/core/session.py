from __future__ import annotations

from datetime import UTC, datetime, timedelta


SESSION_CONFIRMATION_WINDOW = timedelta(hours=1)
SESSION_ABSOLUTE_TIMEOUT = timedelta(hours=12)


def session_expires_at(created_at: datetime, confirmed_at: datetime) -> datetime:
    """Return the earlier consent-window or absolute deadline."""
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if confirmed_at.tzinfo is None:
        confirmed_at = confirmed_at.replace(tzinfo=UTC)
    return min(
        created_at + SESSION_ABSOLUTE_TIMEOUT,
        confirmed_at + SESSION_CONFIRMATION_WINDOW,
    )


def session_has_expired(
    created_at: datetime, last_activity_at: datetime, now: datetime
) -> bool:
    return now >= session_expires_at(created_at, last_activity_at)
