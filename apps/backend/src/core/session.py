from __future__ import annotations

from datetime import UTC, datetime, timedelta


SESSION_IDLE_TIMEOUT = timedelta(minutes=30)
SESSION_ABSOLUTE_TIMEOUT = timedelta(hours=12)


def session_has_expired(
    created_at: datetime, last_activity_at: datetime, now: datetime
) -> bool:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if last_activity_at.tzinfo is None:
        last_activity_at = last_activity_at.replace(tzinfo=UTC)
    return (
        now - created_at >= SESSION_ABSOLUTE_TIMEOUT
        or now - last_activity_at >= SESSION_IDLE_TIMEOUT
    )
