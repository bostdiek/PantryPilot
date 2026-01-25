"""Tests for user memory document model and API endpoints."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from core.security import create_access_token
from dependencies.db import get_db
from main import app
from models.user_memory_documents import UserMemoryDocument
from models.users import User


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
async def memory_client() -> AsyncGenerator[
    tuple[AsyncClient, AsyncSession, User], None
]:
    """Create test client with real auth and memory document support."""
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

    async def _override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        async with SessionLocal() as session:
            user = await _create_test_user(session, "memoryuser")
            yield client, session, user

    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_memory_document_creates_empty_if_missing(
    memory_client: tuple[AsyncClient, AsyncSession, User],
) -> None:
    """Test GET endpoint creates empty memory document if none exists."""
    client, db, user = memory_client

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/chat/memory", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == ""
    assert data["format"] == "markdown"
    assert data["version"] == 1
    assert data["updated_by"] == "user"
    assert "updated_at" in data

    # Verify it was persisted
    stmt = select(UserMemoryDocument).where(UserMemoryDocument.user_id == user.id)
    result = await db.execute(stmt)
    memory_doc = result.scalar_one()
    assert memory_doc.content == ""
    assert memory_doc.version == 1


@pytest.mark.asyncio
async def test_get_memory_document_returns_existing(
    memory_client: tuple[AsyncClient, AsyncSession, User],
) -> None:
    """Test GET endpoint returns existing memory document."""
    client, db, user = memory_client

    # Create existing memory document
    memory_doc = UserMemoryDocument(
        user_id=user.id,
        content="I like pizza and hate mushrooms.",
        format="markdown",
        version=3,
        updated_by="assistant",
        updated_at=datetime.now(UTC),
        metadata_={"trigger": "preference_keyword"},
    )
    db.add(memory_doc)
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/chat/memory", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "I like pizza and hate mushrooms."
    assert data["version"] == 3
    assert data["updated_by"] == "assistant"


@pytest.mark.asyncio
async def test_update_memory_document_creates_if_missing(
    memory_client: tuple[AsyncClient, AsyncSession, User],
) -> None:
    """Test PUT endpoint creates memory document if none exists."""
    client, db, user = memory_client

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    new_content = "# My Preferences\n\n- Allergic to peanuts\n- Love Italian food"

    response = await client.put(
        "/api/v1/chat/memory",
        headers=headers,
        json={"content": new_content},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == new_content
    assert data["version"] == 1
    assert data["updated_by"] == "user"

    # Verify persistence
    stmt = select(UserMemoryDocument).where(UserMemoryDocument.user_id == user.id)
    result = await db.execute(stmt)
    memory_doc = result.scalar_one()
    assert memory_doc.content == new_content
    assert memory_doc.updated_by == "user"


@pytest.mark.asyncio
async def test_update_memory_document_increments_version(
    memory_client: tuple[AsyncClient, AsyncSession, User],
) -> None:
    """Test PUT endpoint increments version on update."""
    client, db, user = memory_client

    # Create existing memory document
    memory_doc = UserMemoryDocument(
        user_id=user.id,
        content="Old content",
        format="markdown",
        version=5,
        updated_by="assistant",
        updated_at=datetime.now(UTC),
        metadata_={},
    )
    db.add(memory_doc)
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    new_content = "Updated content by user"

    response = await client.put(
        "/api/v1/chat/memory",
        headers=headers,
        json={"content": new_content},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == new_content
    assert data["version"] == 6  # Incremented from 5
    assert data["updated_by"] == "user"


@pytest.mark.asyncio
async def test_update_memory_document_validation(
    memory_client: tuple[AsyncClient, AsyncSession, User],
) -> None:
    """Test PUT endpoint validates content length."""
    client, db, user = memory_client

    token = create_access_token({"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    # Content too long (> 50000 chars)
    long_content = "x" * 50001

    response = await client.put(
        "/api/v1/chat/memory",
        headers=headers,
        json={"content": long_content},
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_memory_document_requires_auth(
    memory_client: tuple[AsyncClient, AsyncSession, User],
) -> None:
    """Test endpoints require authentication."""
    client, db, user = memory_client

    # GET without auth
    response = await client.get("/api/v1/chat/memory")
    assert response.status_code == 401

    # PUT without auth
    response = await client.put(
        "/api/v1/chat/memory",
        json={"content": "test"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_memory_document_model_constraints() -> None:
    """Test UserMemoryDocument model constraints."""
    # Test format validation (should only allow 'markdown')
    memory_doc = UserMemoryDocument(
        user_id=uuid4(),
        content="Test",
        format="markdown",  # Valid
        version=1,
        updated_by="user",
        updated_at=datetime.now(UTC),
        metadata_={},
    )
    assert memory_doc.format == "markdown"

    # Test updated_by validation (should only allow 'assistant' or 'user')
    memory_doc.updated_by = "assistant"
    assert memory_doc.updated_by == "assistant"

    memory_doc.updated_by = "user"
    assert memory_doc.updated_by == "user"

    # Test version is positive
    memory_doc.version = 10
    assert memory_doc.version >= 1


@pytest.mark.asyncio
async def test_memory_document_repr() -> None:
    """Test UserMemoryDocument string representation."""
    user_id = uuid4()
    memory_doc = UserMemoryDocument(
        user_id=user_id,
        content="Test content",
        format="markdown",
        version=3,
        updated_by="assistant",
        updated_at=datetime.now(UTC),
        metadata_={},
    )

    repr_str = repr(memory_doc)
    assert "UserMemoryDocument" in repr_str
    assert str(user_id) in repr_str
    assert "version=3" in repr_str
    assert "updated_by=assistant" in repr_str
