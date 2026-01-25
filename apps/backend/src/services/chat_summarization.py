"""Conversation summarization policy (MVP scaffolding).

This module defines when the backend should attempt to update
`chat_conversations.summary`.

Actual summarization (LLM call) will be implemented later; for now we provide
a deterministic policy hook and a small helper for updating fields.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from models.chat_conversations import ChatConversation


SUMMARY_MIN_MESSAGES_BETWEEN_UPDATES: int = 10
SUMMARY_MIN_AGE_BETWEEN_UPDATES: timedelta = timedelta(hours=6)


def should_update_summary(
    conversation: ChatConversation,
    *,
    new_message_count_since_last_summary: int,
    now: datetime | None = None,
) -> bool:
    """Return True when the summary should be refreshed.

    Policy (simple + conservative):
    - Avoid updating too frequently.
    - Require a minimum number of new messages since last update.
    """

    if new_message_count_since_last_summary < SUMMARY_MIN_MESSAGES_BETWEEN_UPDATES:
        return False

    if conversation.summary_updated_at is None:
        return True

    current_time = now or datetime.now(UTC)
    return (
        current_time - conversation.summary_updated_at
    ) >= SUMMARY_MIN_AGE_BETWEEN_UPDATES
