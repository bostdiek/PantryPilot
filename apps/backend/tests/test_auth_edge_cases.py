"""Auth edge case tests (unknown user, missing DB user for token)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from core.security import create_access_token
from dependencies.auth import get_current_user
from dependencies.db import get_db
from main import app
from models.base import Base
from models.users import User


@pytest_asyncio.fixture
async def user_db() -> AsyncGenerator[AsyncSession, None]:
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", future=True, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync: Base.metadata.create_all(sync, tables=[User.__table__])
        )
    SessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_http(user_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield user_db

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_login_unknown_username(auth_http: AsyncClient):
    resp = await auth_http.post(
        "/api/v1/auth/login",
        data={"username": "doesnotexist", "password": "whatever"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    assert resp.json()["detail"] == "Incorrect username or password"


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(user_db: AsyncSession):
    ghost_id = uuid4()
    token = create_access_token(
        {"sub": str(ghost_id)}, expires_delta=timedelta(minutes=5)
    )
    with pytest.raises(HTTPException) as exc:
        await get_current_user(user_db, token)  # type: ignore[arg-type]
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
