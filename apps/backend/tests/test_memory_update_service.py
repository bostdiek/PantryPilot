"""Tests for memory update service."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from models.user_memory_documents import UserMemoryDocument
from models.users import User
from services.memory_update import MemoryUpdateService


async def _create_test_user(db: AsyncSession, username: str = "testuser") -> User:
    """Create a test user."""
    from core.security import get_password_hash

    user = User(
        id=uuid4(),
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("password123"),
        first_name="Test",
        last_name="User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create isolated database session for service tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        # Create minimal tables compatible with SQLite
        await conn.exec_driver_sql(
            """
            CREATE TABLE users (
                id BLOB PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                is_verified INTEGER DEFAULT 0,
                first_name TEXT,
                last_name TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        await conn.exec_driver_sql(
            """
            CREATE TABLE user_memory_documents (
                user_id BLOB PRIMARY KEY,
                content TEXT DEFAULT '',
                format TEXT DEFAULT 'markdown',
                version INTEGER DEFAULT 1,
                updated_at TEXT,
                updated_by TEXT DEFAULT 'assistant',
                metadata TEXT DEFAULT '{}'
            )
            """
        )

    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_should_update_memory_preference_keywords(
    db_session: AsyncSession,
) -> None:
    """Test memory update triggers on preference keywords."""
    service = MemoryUpdateService(db_session)
    user_id = uuid4()

    # Test various preference keywords
    test_cases = [
        ("I prefer chicken over beef", True),
        ("I like Italian food", True),
        ("I dislike mushrooms", True),
        ("I hate onions", True),
        ("I love pasta", True),
        ("I always eat breakfast", True),
        ("I never eat seafood", True),
        ("I'm allergic to peanuts", True),
        ("I have a dairy allergy", True),
        ("My dietary restriction is vegetarian", True),
        ("I avoid gluten", True),
        ("Pizza is my favorite", True),
        ("What's for dinner?", False),  # No preference keyword
        ("Hello assistant", False),  # No preference keyword
    ]

    for message, expected in test_cases:
        result = await service.should_update_memory(user_id, message)
        assert result == expected, f"Failed for message: {message}"


@pytest.mark.asyncio
async def test_should_update_memory_explicit_keywords(
    db_session: AsyncSession,
) -> None:
    """Test memory update triggers on explicit memory keywords."""
    service = MemoryUpdateService(db_session)
    user_id = uuid4()

    test_cases = [
        ("Remember that I'm vegetarian", True),
        ("Don't forget I have a nut allergy", True),
        ("Keep in mind I prefer spicy food", True),
        ("Note that I dislike cilantro", True),
        ("For future reference, I love Mexican cuisine", True),
        ("Just asking a question", False),
        ("What's the weather today?", False),
    ]

    for message, expected in test_cases:
        result = await service.should_update_memory(user_id, message)
        assert result == expected, f"Failed for message: {message}"


@pytest.mark.asyncio
async def test_should_update_memory_periodic_checkpoint(
    db_session: AsyncSession,
) -> None:
    """Test memory update triggers on periodic checkpoints."""
    service = MemoryUpdateService(db_session, message_threshold=10)
    user_id = uuid4()

    # Non-triggering message counts
    assert not await service.should_update_memory(
        user_id, "random message", message_count=5
    )
    assert not await service.should_update_memory(
        user_id, "another message", message_count=9
    )

    # Triggering checkpoint (every 10 messages)
    assert await service.should_update_memory(
        user_id, "checkpoint message", message_count=10
    )
    assert await service.should_update_memory(
        user_id, "another checkpoint", message_count=20
    )
    assert await service.should_update_memory(
        user_id, "third checkpoint", message_count=30
    )


@pytest.mark.asyncio
async def test_update_memory_content_creates_new(
    db_session: AsyncSession,
) -> None:
    """Test updating memory content creates new document if none exists."""
    service = MemoryUpdateService(db_session)
    user = await _create_test_user(db_session, "memuser1")

    content = "User prefers vegetarian meals and dislikes spicy food."
    metadata = {"trigger": "preference_keyword", "source": "chat_message"}

    memory_doc = await service.update_memory_content(user.id, content, metadata)

    assert memory_doc.user_id == user.id
    assert memory_doc.content == content
    assert memory_doc.version == 1
    assert memory_doc.updated_by == "assistant"
    assert memory_doc.metadata_.get("trigger") == "preference_keyword"
    assert "updated_at_iso" in memory_doc.metadata_

    # Verify persistence
    stmt = select(UserMemoryDocument).where(UserMemoryDocument.user_id == user.id)
    result = await db_session.execute(stmt)
    persisted = result.scalar_one()
    assert persisted.content == content


@pytest.mark.asyncio
async def test_update_memory_content_updates_existing(
    db_session: AsyncSession,
) -> None:
    """Test updating memory content increments version on existing document."""
    service = MemoryUpdateService(db_session)
    user = await _create_test_user(db_session, "memuser2")

    # Create existing memory document
    existing = UserMemoryDocument(
        user_id=user.id,
        content="Old preferences",
        format="markdown",
        version=3,
        updated_by="user",
        updated_at=datetime.now(UTC),
        metadata_={"old_key": "old_value"},
    )
    db_session.add(existing)
    await db_session.commit()

    # Update with new content
    new_content = "Updated preferences: loves pasta, allergic to shellfish."
    new_metadata = {"trigger": "explicit_memory", "conversation_id": "abc123"}

    updated = await service.update_memory_content(user.id, new_content, new_metadata)

    assert updated.content == new_content
    assert updated.version == 4  # Incremented from 3
    assert updated.updated_by == "assistant"
    assert updated.metadata_.get("old_key") == "old_value"  # Preserved
    assert updated.metadata_.get("trigger") == "explicit_memory"  # New
    assert "updated_at_iso" in updated.metadata_


@pytest.mark.asyncio
async def test_get_memory_document_returns_none_if_missing(
    db_session: AsyncSession,
) -> None:
    """Test get_memory_document returns None if no document exists."""
    service = MemoryUpdateService(db_session)
    user = await _create_test_user(db_session, "memuser3")

    memory_doc = await service.get_memory_document(user.id)
    assert memory_doc is None


@pytest.mark.asyncio
async def test_get_memory_document_returns_existing(
    db_session: AsyncSession,
) -> None:
    """Test get_memory_document returns existing document."""
    service = MemoryUpdateService(db_session)
    user = await _create_test_user(db_session, "memuser4")

    # Create memory document
    existing = UserMemoryDocument(
        user_id=user.id,
        content="Test content",
        format="markdown",
        version=2,
        updated_by="assistant",
        updated_at=datetime.now(UTC),
        metadata_={},
    )
    db_session.add(existing)
    await db_session.commit()

    memory_doc = await service.get_memory_document(user.id)
    assert memory_doc is not None
    assert memory_doc.content == "Test content"
    assert memory_doc.version == 2


@pytest.mark.asyncio
async def test_create_diff_summary() -> None:
    """Test diff summary creation for SSE events."""
    old_content = "I like pizza."
    new_content = "I like pizza and pasta. I dislike mushrooms."

    diff = MemoryUpdateService.create_diff_summary(old_content, new_content)

    assert diff["old_length"] == len(old_content)
    assert diff["new_length"] == len(new_content)
    assert diff["changed"] is True
    assert diff["diff_chars"] == len(new_content) - len(old_content)

    # Test unchanged content
    diff_unchanged = MemoryUpdateService.create_diff_summary(old_content, old_content)
    assert diff_unchanged["changed"] is False
    assert diff_unchanged["diff_chars"] == 0


@pytest.mark.asyncio
async def test_memory_service_custom_threshold(
    db_session: AsyncSession,
) -> None:
    """Test custom message threshold configuration."""
    service = MemoryUpdateService(db_session, message_threshold=5)
    user_id = uuid4()

    # Should trigger at 5 instead of 10
    assert await service.should_update_memory(user_id, "message", message_count=5)
    assert await service.should_update_memory(user_id, "message", message_count=10)
    assert not await service.should_update_memory(user_id, "message", message_count=7)
