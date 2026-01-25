from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from models.chat_conversations import ChatConversation
from services.chat_summarization import (
    SUMMARY_MIN_AGE_BETWEEN_UPDATES,
    SUMMARY_MIN_MESSAGES_BETWEEN_UPDATES,
    should_update_summary,
)


def test_should_update_summary_requires_min_new_messages() -> None:
    conversation = ChatConversation(user_id=uuid.uuid4())

    assert (
        should_update_summary(
            conversation,
            new_message_count_since_last_summary=SUMMARY_MIN_MESSAGES_BETWEEN_UPDATES
            - 1,
            now=datetime(2026, 1, 1, tzinfo=UTC),
        )
        is False
    )


def test_should_update_summary_first_summary_allowed_after_threshold() -> None:
    conversation = ChatConversation(user_id=uuid.uuid4())
    conversation.summary_updated_at = None

    assert (
        should_update_summary(
            conversation,
            new_message_count_since_last_summary=SUMMARY_MIN_MESSAGES_BETWEEN_UPDATES,
            now=datetime(2026, 1, 1, tzinfo=UTC),
        )
        is True
    )


def test_should_update_summary_respects_min_age_between_updates() -> None:
    conversation = ChatConversation(user_id=uuid.uuid4())
    last = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    conversation.summary_updated_at = last

    assert (
        should_update_summary(
            conversation,
            new_message_count_since_last_summary=SUMMARY_MIN_MESSAGES_BETWEEN_UPDATES,
            now=last + SUMMARY_MIN_AGE_BETWEEN_UPDATES - timedelta(seconds=1),
        )
        is False
    )

    assert (
        should_update_summary(
            conversation,
            new_message_count_since_last_summary=SUMMARY_MIN_MESSAGES_BETWEEN_UPDATES,
            now=last + SUMMARY_MIN_AGE_BETWEEN_UPDATES,
        )
        is True
    )
