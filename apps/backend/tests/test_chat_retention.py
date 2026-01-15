from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta

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

from services.chat_retention import (
    CHAT_MESSAGE_MAX_PER_CONVERSATION,
    CHAT_MESSAGE_TTL_DAYS,
    enforce_chat_message_retention,
)


@pytest_asyncio.fixture
async def chat_retention_db() -> AsyncGenerator[AsyncSession, None]:
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE TABLE users (id TEXT PRIMARY KEY)")
        await conn.exec_driver_sql(
            "CREATE TABLE chat_conversations ("
            "id TEXT PRIMARY KEY, "
            "user_id TEXT NOT NULL)"
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE chat_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content_blocks TEXT NOT NULL,
                metadata TEXT NOT NULL,
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


async def _seed_message(
    db: AsyncSession,
    *,
    message_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    created_at: datetime,
) -> None:
    await db.execute(
        sa.text(
            """
            INSERT INTO chat_messages (
                id, conversation_id, user_id, role, content_blocks, metadata, created_at
            ) VALUES (
                :id, :conversation_id, :user_id, 'user', '[]', '{}', :created_at
            )
            """
        ),
        {
            "id": message_id.hex,
            "conversation_id": conversation_id.hex,
            "user_id": user_id.hex,
            "created_at": created_at,
        },
    )


async def _count_messages(
    db: AsyncSession, *, where: str = "", params: dict | None = None
) -> int:
    stmt = sa.text(f"SELECT COUNT(*) FROM chat_messages {where}")
    result = await db.execute(stmt, params or {})
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_retention_deletes_messages_older_than_ttl(
    chat_retention_db: AsyncSession,
) -> None:
    db = chat_retention_db

    conversation_id = uuid.uuid4()
    user_id = uuid.uuid4()

    now = datetime(2026, 1, 15, 12, 0, 0)
    old = now - timedelta(days=CHAT_MESSAGE_TTL_DAYS + 1)
    recent = now - timedelta(days=1)

    await _seed_message(
        db,
        message_id=uuid.uuid4(),
        conversation_id=conversation_id,
        user_id=user_id,
        created_at=old,
    )
    await _seed_message(
        db,
        message_id=uuid.uuid4(),
        conversation_id=conversation_id,
        user_id=user_id,
        created_at=recent,
    )
    await db.commit()

    deleted = await enforce_chat_message_retention(db, now=now)

    assert deleted == 1
    assert await _count_messages(db) == 1


@pytest.mark.asyncio
async def test_retention_enforces_size_cap_per_conversation(
    chat_retention_db: AsyncSession,
) -> None:
    db = chat_retention_db

    conversation_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime(2026, 1, 15, 12, 0, 0)

    ids: list[str] = []
    # Newest has the greatest created_at; enforce_chat_message_retention keeps newest N.
    for i in range(CHAT_MESSAGE_MAX_PER_CONVERSATION + 10):
        message_id = uuid.uuid4()
        ids.append(message_id.hex)
        await _seed_message(
            db,
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            created_at=now - timedelta(minutes=i),
        )
    await db.commit()

    deleted = await enforce_chat_message_retention(db, now=now)

    assert deleted == 10
    assert (
        await _count_messages(
            db,
            where="WHERE conversation_id = :cid",
            params={"cid": conversation_id.hex},
        )
    ) == CHAT_MESSAGE_MAX_PER_CONVERSATION

    # Oldest 10 (last inserted) should be deleted.
    expected_deleted_ids = set(ids[-10:])
    remaining = await db.execute(
        sa.text("SELECT id FROM chat_messages WHERE conversation_id = :cid"),
        {"cid": conversation_id.hex},
    )
    remaining_ids = {row[0] for row in remaining.fetchall()}
    assert expected_deleted_ids.isdisjoint(remaining_ids)


@pytest.mark.asyncio
async def test_retention_scopes_by_conversation_id(
    chat_retention_db: AsyncSession,
) -> None:
    db = chat_retention_db

    conversation_a = uuid.uuid4()
    conversation_b = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime(2026, 1, 15, 12, 0, 0)

    for i in range(CHAT_MESSAGE_MAX_PER_CONVERSATION + 10):
        await _seed_message(
            db,
            message_id=uuid.uuid4(),
            conversation_id=conversation_a,
            user_id=user_id,
            created_at=now - timedelta(minutes=i),
        )
        await _seed_message(
            db,
            message_id=uuid.uuid4(),
            conversation_id=conversation_b,
            user_id=user_id,
            created_at=now - timedelta(minutes=i),
        )
    await db.commit()

    deleted = await enforce_chat_message_retention(
        db, conversation_id=conversation_a, now=now
    )

    assert deleted == 10
    assert (
        await _count_messages(
            db,
            where="WHERE conversation_id = :cid",
            params={"cid": conversation_a.hex},
        )
    ) == CHAT_MESSAGE_MAX_PER_CONVERSATION
    assert (
        await _count_messages(
            db,
            where="WHERE conversation_id = :cid",
            params={"cid": conversation_b.hex},
        )
    ) == CHAT_MESSAGE_MAX_PER_CONVERSATION + 10


@pytest.mark.asyncio
async def test_retention_scopes_by_user_id(chat_retention_db: AsyncSession) -> None:
    db = chat_retention_db

    conversation_id = uuid.uuid4()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    now = datetime(2026, 1, 15, 12, 0, 0)

    for i in range(CHAT_MESSAGE_MAX_PER_CONVERSATION + 10):
        await _seed_message(
            db,
            message_id=uuid.uuid4(),
            conversation_id=conversation_id,
            user_id=user_a,
            created_at=now - timedelta(minutes=i),
        )
        await _seed_message(
            db,
            message_id=uuid.uuid4(),
            conversation_id=conversation_id,
            user_id=user_b,
            created_at=now - timedelta(minutes=i),
        )
    await db.commit()

    deleted = await enforce_chat_message_retention(db, user_id=user_a, now=now)

    assert deleted == 10
    assert (
        await _count_messages(
            db,
            where="WHERE conversation_id = :cid AND user_id = :uid",
            params={"cid": conversation_id.hex, "uid": user_a.hex},
        )
    ) == CHAT_MESSAGE_MAX_PER_CONVERSATION
    assert (
        await _count_messages(
            db,
            where="WHERE conversation_id = :cid AND user_id = :uid",
            params={"cid": conversation_id.hex, "uid": user_b.hex},
        )
    ) == CHAT_MESSAGE_MAX_PER_CONVERSATION + 10
