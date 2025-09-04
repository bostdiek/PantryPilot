"""User CRUD helper & schema tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from core.security import get_password_hash
from crud.user import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
)
from dependencies.db import get_db
from main import app
from models.base import Base
from models.users import User
from schemas.user import UserInDB, UserPublic


@pytest_asyncio.fixture
async def db_user_only() -> AsyncGenerator[AsyncSession, None]:
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


def test_user_schema_serialization():
    uid = uuid4()
    public = UserPublic(id=uid, email="u@example.com", username="user")
    assert public.id == uid
    in_db = UserInDB(
        id=uid,
        email="u@example.com",
        username="user",
        hashed_password="hash",
        first_name=None,
        last_name=None,
    )
    payload = in_db.model_dump()
    assert payload["hashed_password"] == "hash"


@pytest_asyncio.fixture
async def crud_db_http(db_user_only: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_user_only

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_user_crud_helpers(db_user_only: AsyncSession):  # noqa: D103
    assert await get_user_by_username(db_user_only, "alpha") is None
    user = await create_user(
        db_user_only,
        email="alpha@example.com",
        username="alpha",
        hashed_password=get_password_hash("pw-secure"),
        first_name="Al",
        last_name="Pha",
    )
    assert await get_user_by_username(db_user_only, "alpha") is not None
    assert await get_user_by_email(db_user_only, "alpha@example.com") is not None
    assert await get_user_by_id(db_user_only, user.id) is not None
    assert await get_user_by_username(db_user_only, "missing") is None
    assert await get_user_by_email(db_user_only, "missing@example.com") is None
