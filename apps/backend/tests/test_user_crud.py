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


@pytest.mark.asyncio
async def test_user_crud_set_verified(db_user_only: AsyncSession):
    """Test set_verified marks user as verified."""
    from crud.user import user_crud

    # Create unverified user
    user = await create_user(
        db_user_only,
        email="verify@example.com",
        username="verifyuser",
        hashed_password=get_password_hash("testpass123"),
    )
    assert user.is_verified is False

    # Mark as verified
    updated_user = await user_crud.set_verified(db_user_only, user)

    assert updated_user.is_verified is True
    assert updated_user.id == user.id


@pytest.mark.asyncio
async def test_user_crud_update_password(db_user_only: AsyncSession):
    """Test update_password changes the user's password hash."""
    from core.security import verify_password
    from crud.user import user_crud

    # Create user with original password
    user = await create_user(
        db_user_only,
        email="pwchange@example.com",
        username="pwchangeuser",
        hashed_password=get_password_hash("originalpass123"),
    )

    # Verify original password works
    assert verify_password("originalpass123", user.hashed_password)

    # Update password
    new_hash = get_password_hash("newpassword456")
    updated_user = await user_crud.update_password(db_user_only, user, new_hash)

    # Verify new password works and old doesn't
    assert verify_password("newpassword456", updated_user.hashed_password)
    assert not verify_password("originalpass123", updated_user.hashed_password)


@pytest.mark.asyncio
async def test_user_crud_update_profile(db_user_only: AsyncSession):
    """Test update method for user profile changes."""
    from crud.user import user_crud
    from schemas.user_preferences import UserProfileUpdate

    # Create user
    user = await create_user(
        db_user_only,
        email="profile@example.com",
        username="profileuser",
        hashed_password=get_password_hash("testpass123"),
        first_name="Original",
        last_name="Name",
    )

    # Update profile
    update_data = UserProfileUpdate(first_name="Updated", last_name="Person")
    updated_user = await user_crud.update(db_user_only, user, update_data)

    assert updated_user.first_name == "Updated"
    assert updated_user.last_name == "Person"
    assert updated_user.id == user.id


@pytest.mark.asyncio
async def test_user_crud_duplicate_user_raises_error(db_user_only: AsyncSession):
    """Test creating duplicate user raises DuplicateUserError."""
    from core.exceptions import DuplicateUserError
    from crud.user import user_crud

    # Create first user
    await user_crud.create(
        db_user_only,
        email="dupe@example.com",
        username="dupeuser",
        hashed_password=get_password_hash("testpass123"),
    )

    # Try to create with same email
    with pytest.raises(DuplicateUserError):
        await user_crud.create(
            db_user_only,
            email="dupe@example.com",
            username="different",
            hashed_password=get_password_hash("testpass123"),
        )


@pytest.mark.asyncio
async def test_user_crud_duplicate_username_raises_error(db_user_only: AsyncSession):
    """Test creating user with duplicate username raises DuplicateUserError."""
    from core.exceptions import DuplicateUserError
    from crud.user import user_crud

    # Create first user
    await user_crud.create(
        db_user_only,
        email="first@example.com",
        username="sameusername",
        hashed_password=get_password_hash("testpass123"),
    )

    # Try to create with same username
    with pytest.raises(DuplicateUserError):
        await user_crud.create(
            db_user_only,
            email="second@example.com",
            username="sameusername",
            hashed_password=get_password_hash("testpass123"),
        )
