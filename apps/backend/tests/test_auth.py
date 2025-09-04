"""Authorization & authentication tests for PantryPilot.

Covers:
- Successful login returns token
- Login failure wrong password
- Protected endpoint 401 without token (real dependency)
- Protected endpoint 200 with valid token
- Expired token rejected
- Invalid token rejected
- Token missing `sub` claim rejected
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import get_settings
from core.security import create_access_token, get_password_hash
from dependencies.auth import get_current_user
from dependencies.db import get_db
from main import app
from models.base import Base
from models.meal_history import Meal
from models.users import User


settings = get_settings()


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


async def _create_user(db: AsyncSession, username: str = "alice") -> User:
    user = User(
        username=username,
        email=f"{username}@example.test",
        hashed_password=get_password_hash("secret"),
        first_name="A",
        last_name="User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_login_success(auth_client: tuple[AsyncClient, AsyncSession]):
    client, db = auth_client
    user = await _create_user(db)
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": user.username, "password": "secret"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == status.HTTP_200_OK
    payload = resp.json()
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(auth_client: tuple[AsyncClient, AsyncSession]):
    client, db = auth_client
    user = await _create_user(db, username="bob")

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": user.username, "password": "not-secret"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_protected_endpoint_requires_token(
    auth_client: tuple[AsyncClient, AsyncSession],
):
    client, _ = auth_client
    resp = await client.get("/api/v1/mealplans/weekly?start=2025-01-14")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.headers["www-authenticate"].lower().startswith("bearer")


@pytest.mark.asyncio
async def test_protected_endpoint_with_token(
    auth_client: tuple[AsyncClient, AsyncSession],
):
    client, db = auth_client
    user = await _create_user(db, username="carol")
    token = create_access_token(
        {"sub": str(user.id)}, expires_delta=timedelta(minutes=5)
    )
    resp = await client.get(
        "/api/v1/mealplans/weekly?start=2025-01-14",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code != status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_expired_token_rejected(auth_client: tuple[AsyncClient, AsyncSession]):
    client, db = auth_client
    user = await _create_user(db, username="dave")
    expired = create_access_token(
        {"sub": str(user.id)}, expires_delta=timedelta(minutes=-1)
    )
    resp = await client.get(
        "/api/v1/mealplans/weekly?start=2025-01-12",
        headers={"Authorization": f"Bearer {expired}"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json()["detail"] in {
        "Could not validate credentials",
        "Token missing subject",
    }


@pytest.mark.asyncio
async def test_invalid_token(auth_client: tuple[AsyncClient, AsyncSession]):
    client, _ = auth_client
    # Completely invalid token string
    resp = await client.get(
        "/api/v1/mealplans/weekly?start=2025-01-12",
        headers={"Authorization": "Bearer not.a.jwt"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_token_missing_sub_claim(auth_client: tuple[AsyncClient, AsyncSession]):
    client, db = auth_client
    # Create user so DB not empty; but build token without sub
    await _create_user(db, username="eve")
    no_sub = jwt.encode(
        {"exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    resp = await client.get(
        "/api/v1/mealplans/weekly?start=2025-01-12",
        headers={"Authorization": f"Bearer {no_sub}"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
