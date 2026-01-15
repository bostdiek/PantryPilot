"""Retention enforcement for chat messages.

Policy (locked by Story 2 research):
- Hard TTL delete: delete messages older than 90 days.
- Size cap: keep newest 50 remaining per conversation.

This is implemented as an application-level job so it can run periodically
(e.g., cron, scheduled task, or a management command).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from models.chat_messages import ChatMessage


CHAT_MESSAGE_TTL_DAYS: int = 90
CHAT_MESSAGE_MAX_PER_CONVERSATION: int = 50


async def enforce_chat_message_retention(
    db: AsyncSession,
    *,
    conversation_id: UUID | None = None,
    user_id: UUID | None = None,
    now: datetime | None = None,
) -> int:
    """Enforce retention for chat messages.

    Returns the number of messages deleted.

    Scope:
    - If `conversation_id` is provided, enforcement is limited to that conversation.
    - If `user_id` is provided, enforcement is limited to that user's messages.
    """

    deleted_total = 0
    cutoff = (now or datetime.now(UTC)) - timedelta(days=CHAT_MESSAGE_TTL_DAYS)

    ttl_filters: list[sa.ColumnElement[bool]] = [ChatMessage.created_at < cutoff]
    if conversation_id is not None:
        ttl_filters.append(ChatMessage.conversation_id == conversation_id)
    if user_id is not None:
        ttl_filters.append(ChatMessage.user_id == user_id)

    ttl_delete = sa.delete(ChatMessage).where(sa.and_(*ttl_filters))
    ttl_result = await db.execute(ttl_delete)
    deleted_total += int(ttl_result.rowcount or 0)

    # Size cap enforcement using a window function (Postgres):
    # keep newest N messages per conversation.
    base_query = sa.select(
        ChatMessage.id,
        sa.func.row_number()
        .over(
            partition_by=ChatMessage.conversation_id,
            order_by=ChatMessage.created_at.desc(),
        )
        .label("rn"),
    )

    cap_filters: list[sa.ColumnElement[bool]] = []
    if conversation_id is not None:
        cap_filters.append(ChatMessage.conversation_id == conversation_id)
    if user_id is not None:
        cap_filters.append(ChatMessage.user_id == user_id)

    if cap_filters:
        base_query = base_query.where(sa.and_(*cap_filters))

    ranked = base_query.subquery("ranked_messages")
    ids_to_delete = sa.select(ranked.c.id).where(
        ranked.c.rn > CHAT_MESSAGE_MAX_PER_CONVERSATION
    )

    cap_delete = sa.delete(ChatMessage).where(ChatMessage.id.in_(ids_to_delete))
    cap_result = await db.execute(cap_delete)
    deleted_total += int(cap_result.rowcount or 0)

    if deleted_total:
        await db.commit()

    return deleted_total
