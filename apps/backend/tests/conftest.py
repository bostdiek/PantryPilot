"""Shared test fixtures for pytest.

We set minimal env defaults (e.g. SECRET_KEY) early so importing modules
that instantiate settings (core.security) succeeds without needing an
external .env file during tests.
"""

import os
import uuid
from collections.abc import AsyncGenerator, Generator
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


os.environ.setdefault("SECRET_KEY", "test-secret-key")

from core.config import get_settings
from core.security import get_password_hash
from dependencies.auth import get_current_user
from dependencies.db import get_db
from main import app
from models.base import Base
from models.meal_history import Meal
from models.user_preferences import UserPreferences
from models.users import User


settings = get_settings()


async def _ensure_demo_user(db: AsyncSession) -> User:
    """Create (or fetch) a demo user for non-auth focused tests.

    These tests previously assumed public endpoints; now that most routes are
    protected we override auth to always return this user. Auth-specific tests
    remove this override to exercise the real dependency chain.
    """
    result = await db.execute(
        # Use ORM-style select for better typing and consistent result shapes
        select(User).limit(1)
    )
    user = result.scalars().one_or_none()
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

    def one_or_none(self):  # pragma: no cover - trivial
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


@pytest.fixture
def payload_namespace():
    """Factory fixture that builds SimpleNamespace-like payloads for unit tests.

    Use this in unit tests that directly call route functions to bypass Pydantic
    validation and exercise manual branches.
    """

    def _make(
        username: str = "testuser",
        email: str = "test@test.com",
        password: str = "securepassword123",
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

    return _make


@pytest_asyncio.fixture
async def auth_client() -> AsyncGenerator[tuple[AsyncClient, AsyncSession], None]:
    """Client + real in-memory SQLite DB with full schema for auth tests.

    Removes any auth override so routes are actually protected.
    """
    # Ensure no auth override from generic fixtures
    app.dependency_overrides.pop(get_current_user, None)

    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", future=True
    )
    async with engine.begin() as conn:
        # Create minimal subset of tables to satisfy auth & mealplans tests.
        # Avoid Recipe model (Postgres ARRAY) which SQLite can't compile.
        await conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS recipe_names (id BLOB PRIMARY KEY)"
        )
        # Create user_preferences table with SQLite-compatible schema
        await conn.exec_driver_sql("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id BLOB PRIMARY KEY,
                user_id BLOB NOT NULL UNIQUE,
                family_size INTEGER NOT NULL DEFAULT 2,
                default_servings INTEGER NOT NULL DEFAULT 4,
                allergies TEXT NOT NULL DEFAULT '[]',
                dietary_restrictions TEXT NOT NULL DEFAULT '[]',
                theme VARCHAR(20) NOT NULL DEFAULT 'light',
                units VARCHAR(20) NOT NULL DEFAULT 'imperial',
                meal_planning_days INTEGER NOT NULL DEFAULT 7,
                preferred_cuisines TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=[User.__table__, Meal.__table__]
            )
        )

    SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async def _override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        async with SessionLocal() as session:
            yield c, session
    app.dependency_overrides.pop(get_db, None)
    await engine.dispose()
