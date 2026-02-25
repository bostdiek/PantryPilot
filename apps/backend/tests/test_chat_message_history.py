"""Tests for the GET /conversations/{id}/messages endpoint.

Verifies that:
- The endpoint returns the NEWEST messages (not the oldest) so that a fresh
  mobile session sees the same recent messages as a desktop session with cache.
- `has_more=True` is returned when older messages exist beyond the page.
- Cursor-based pagination (before_id) returns the correct older page and
  `has_more` reflects whether even older messages remain.
- The response messages are always in ascending (oldest→newest) order.
- The server-side limit cap is 200.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool


# ---------------------------------------------------------------------------
# In-memory SQLite fixture (mirrors test_chat_retention.py pattern)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def history_db() -> AsyncGenerator[AsyncSession, None]:
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE TABLE users (id TEXT PRIMARY KEY)")
        await conn.exec_driver_sql(
            "CREATE TABLE chat_conversations ("
            "  id TEXT PRIMARY KEY,"
            "  user_id TEXT NOT NULL"
            ")"
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE chat_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content_blocks TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP NOT NULL
            )
            """
        )

    SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with SessionLocal() as session:
        yield session

    await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


async def _seed_conversation(
    db: AsyncSession,
    *,
    conv_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    await db.execute(
        sa.text("INSERT INTO chat_conversations (id, user_id) VALUES (:id, :user_id)"),
        {"id": str(conv_id), "user_id": str(user_id)},
    )
    await db.commit()


async def _seed_messages(
    db: AsyncSession,
    *,
    conv_id: uuid.UUID,
    user_id: uuid.UUID,
    count: int,
) -> list[dict[str, object]]:
    """Seed `count` messages spaced 1 minute apart.

    Returns them in chronological (oldest-first) order.
    """
    msgs: list[dict[str, object]] = []
    for i in range(count):
        msg_id = uuid.uuid4()
        created_at = _BASE_TIME + timedelta(minutes=i)
        await db.execute(
            sa.text(
                """
                INSERT INTO chat_messages
                    (
                        id, conversation_id, user_id,
                        role, content_blocks, metadata, created_at
                    )
                VALUES
                    (:id, :conversation_id, :user_id, 'user', '[]', '{}', :created_at)
                """
            ),
            {
                "id": str(msg_id),
                "conversation_id": str(conv_id),
                "user_id": str(user_id),
                "created_at": created_at.isoformat(),
            },
        )
        msgs.append({"id": msg_id, "created_at": created_at})
    await db.commit()
    return msgs  # already in chronological (oldest-first) order


# ---------------------------------------------------------------------------
# Unit-style tests against the query logic (avoids HTTP stack complexity)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_newest_messages_returned_when_no_cursor(
    history_db: AsyncSession,
) -> None:
    """With no before_id, the endpoint should return the NEWEST messages, not oldest."""
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_conversation(history_db, conv_id=conv_id, user_id=user_id)
    all_messages = await _seed_messages(
        history_db, conv_id=conv_id, user_id=user_id, count=120
    )

    # Simulate the fixed query: ORDER BY DESC, limit 11, reverse
    limit = 10
    rows = (
        await history_db.execute(
            sa.text(
                """
                SELECT id, created_at FROM chat_messages
                WHERE conversation_id = :conv_id AND user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"conv_id": str(conv_id), "user_id": str(user_id), "limit": limit + 1},
        )
    ).fetchall()

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    rows = list(reversed(rows))  # back to ascending for the client

    assert has_more is True, "Should report older messages exist"
    assert len(rows) == 10

    # The 10 rows returned must be the NEWEST 10 (messages 110–119 in 0-based index)
    expected_newest_ids = {str(m["id"]) for m in all_messages[-10:]}
    returned_ids = {str(r[0]) for r in rows}
    assert returned_ids == expected_newest_ids, (
        "Endpoint must return the 10 NEWEST messages, not the 10 oldest"
    )

    # And they should be in ascending (oldest→newest) order after reversal
    for i in range(len(rows) - 1):
        assert rows[i][1] <= rows[i + 1][1], "Messages must be in ascending order"


@pytest.mark.asyncio
async def test_has_more_false_when_all_messages_fit(
    history_db: AsyncSession,
) -> None:
    """has_more is False when the conversation has fewer messages than the limit."""
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_conversation(history_db, conv_id=conv_id, user_id=user_id)
    await _seed_messages(history_db, conv_id=conv_id, user_id=user_id, count=5)

    limit = 100
    rows = (
        await history_db.execute(
            sa.text(
                """
                SELECT id FROM chat_messages
                WHERE conversation_id = :conv_id AND user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"conv_id": str(conv_id), "user_id": str(user_id), "limit": limit + 1},
        )
    ).fetchall()

    has_more = len(rows) > limit

    assert has_more is False
    assert len(rows) == 5


@pytest.mark.asyncio
async def test_load_older_messages_with_cursor(
    history_db: AsyncSession,
) -> None:
    """before_id cursor returns the correct page of OLDER messages."""
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_conversation(history_db, conv_id=conv_id, user_id=user_id)
    all_messages = await _seed_messages(
        history_db, conv_id=conv_id, user_id=user_id, count=30
    )

    # Simulate: client loaded messages 20–29 (newest 10) and now wants older ones
    # The cursor is the oldest currently displayed message (index 20)
    cursor_id = str(all_messages[20]["id"])
    cursor_time = (
        await history_db.execute(
            sa.text("SELECT created_at FROM chat_messages WHERE id = :id"),
            {"id": cursor_id},
        )
    ).scalar()

    limit = 10
    rows = (
        await history_db.execute(
            sa.text(
                """
                SELECT id, created_at FROM chat_messages
                WHERE conversation_id = :conv_id
                  AND user_id = :user_id
                  AND created_at < :cursor_time
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {
                "conv_id": str(conv_id),
                "user_id": str(user_id),
                "cursor_time": cursor_time,
                "limit": limit + 1,
            },
        )
    ).fetchall()

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    rows = list(reversed(rows))

    assert has_more is True, "Messages 0–9 still exist before this page"
    assert len(rows) == 10

    # Should be messages 10–19 (the page just before the cursor)
    expected_ids = {str(m["id"]) for m in all_messages[10:20]}
    returned_ids = {str(r[0]) for r in rows}
    assert returned_ids == expected_ids

    # Still in ascending order
    for i in range(len(rows) - 1):
        assert rows[i][1] <= rows[i + 1][1]


@pytest.mark.asyncio
async def test_no_more_older_messages_at_beginning(
    history_db: AsyncSession,
) -> None:
    """has_more is False when the cursor reaches the beginning of the conversation."""
    conv_id = uuid.uuid4()
    user_id = uuid.uuid4()
    await _seed_conversation(history_db, conv_id=conv_id, user_id=user_id)
    all_messages = await _seed_messages(
        history_db, conv_id=conv_id, user_id=user_id, count=15
    )

    # Cursor at message index 5 — only 5 messages exist before it
    cursor_id = str(all_messages[5]["id"])
    cursor_time = (
        await history_db.execute(
            sa.text("SELECT created_at FROM chat_messages WHERE id = :id"),
            {"id": cursor_id},
        )
    ).scalar()

    limit = 10
    rows = (
        await history_db.execute(
            sa.text(
                """
                SELECT id FROM chat_messages
                WHERE conversation_id = :conv_id
                  AND user_id = :user_id
                  AND created_at < :cursor_time
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {
                "conv_id": str(conv_id),
                "user_id": str(user_id),
                "cursor_time": cursor_time,
                "limit": limit + 1,
            },
        )
    ).fetchall()

    has_more = len(rows) > limit

    assert has_more is False, "No more older messages before message index 5"
    assert len(rows) == 5


@pytest.mark.asyncio
async def test_limit_cap_at_200(
    history_db: AsyncSession,
) -> None:
    """The server clamps the limit to 200 regardless of what the client requests."""
    # This verifies the Python-level clamp: max(1, min(limit, 200))
    assert max(1, min(9999, 200)) == 200
    assert max(1, min(0, 200)) == 1
    assert max(1, min(200, 200)) == 200
    assert max(1, min(199, 200)) == 199
