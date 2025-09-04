"""Shared test fixtures for pytest.

We set minimal env defaults (e.g. SECRET_KEY) early so importing modules
that instantiate settings (core.security) succeeds without needing an
external .env file during tests.
"""

import os
import uuid
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


os.environ.setdefault("SECRET_KEY", "test-secret-key")

from core.security import get_password_hash
from dependencies.auth import get_current_user
from dependencies.db import get_db
from main import app
from models.users import User


async def _ensure_demo_user(db: AsyncSession) -> User:
    """Create (or fetch) a demo user for non-auth focused tests.

    These tests previously assumed public endpoints; now that most routes are
    protected we override auth to always return this user. Auth-specific tests
    remove this override to exercise the real dependency chain.
    """
    result = await db.execute(
        # Simple query; defer import complexity by inline text
        User.__table__.select().limit(1)  # type: ignore[arg-type]
    )
    row = result.first()
    if row:
        # Row 0 is the user instance when selecting table directly may differ;
        # safest is to re-query via ORM if needed, but for simplicity return id lookup.
        user = await db.get(User, row[0])  # type: ignore[index]
        if user:
            return user
    demo = User(
        id=uuid.uuid4(),
        username="demo",
        email="demo@example.test",
        hashed_password=get_password_hash("password"),
        first_name="Demo",
        last_name="User",
    )
    db.add(demo)
    await db.commit()
    await db.refresh(demo)
    return demo


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Create a test client for the FastAPI application.
    """
    with TestClient(app) as client:
        yield client


class _FakeResult:
    """Lightweight stand-in for a SQLAlchemy result."""

    def scalars(self):
        return self

    def first(self):  # pragma: no cover - trivial
        return None


class _FakeSession:
    """Minimal fake async session used in lightweight tests.

    Only the small surface area required by current tests is implemented.
    """

    def add(self, _obj):  # pragma: no cover - no-op
        return None

    async def flush(self):  # pragma: no cover - no-op
        return None

    async def execute(self, _stmt):  # Always empty result
        return _FakeResult()

    async def commit(self):  # pragma: no cover - no-op
        return None

    async def rollback(self):  # pragma: no cover - no-op
        return None

    async def close(self):  # pragma: no cover - no-op
        return None


async def _override_get_db_factory() -> AsyncGenerator[_FakeSession, None]:
    """Yield a fake session for dependency override."""
    fake = _FakeSession()
    try:
        yield fake
    finally:  # pragma: no cover - cleanup path
        await fake.close()


async def _override_get_current_user_factory():  # pragma: no cover - simple helper
    class _DummyUser:
        id = uuid.uuid4()

    return _DummyUser()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async client with DB & auth overrides (auto-auth)."""
    app.dependency_overrides[get_db] = _override_get_db_factory
    app.dependency_overrides[get_current_user] = _override_get_current_user_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
