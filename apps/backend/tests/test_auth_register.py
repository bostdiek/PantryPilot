"""Registration endpoint tests for PantryPilot.

Covers:
- Successful registration returns token and creates user
- Password validation (minimum 12 characters)
- Duplicate username/email handling
- Token usability after registration
- Input validation for username, email, and required fields
- Password hashing verification
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import get_settings
from core.security import verify_password
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


async def _create_existing_user(
    db: AsyncSession, username: str = "existing", email: str = "existing@test.com"
) -> User:
    """Create an existing user for duplicate testing."""
    user = User(
        username=username,
        email=email,
        hashed_password="hashed_password_placeholder",
        first_name="Existing",
        last_name="User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_register_success(auth_client: tuple[AsyncClient, AsyncSession]):
    """Test successful registration with valid data."""
    client, db = auth_client

    registration_data = {
        "username": "newuser123",
        "email": "newuser@test.com",
        "password": "securepassword123",
        "first_name": "New",
        "last_name": "User",
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)

    # Verify 201 status code
    assert resp.status_code == status.HTTP_201_CREATED

    # Verify response contains access_token and token_type
    payload = resp.json()
    assert "access_token" in payload
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"

    # Verify user is created in database
    result = await db.execute(select(User).where(User.username == "newuser123"))
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.username == "newuser123"
    assert created_user.email == "newuser@test.com"
    assert created_user.first_name == "New"
    assert created_user.last_name == "User"

    # Verify password is properly hashed (not stored as plaintext)
    assert created_user.hashed_password != "securepassword123"
    assert verify_password("securepassword123", created_user.hashed_password)


@pytest.mark.asyncio
async def test_register_success_minimal_data(
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """Test successful registration with only required fields."""
    client, db = auth_client

    registration_data = {
        "username": "minimaluser",
        "email": "minimal@test.com",
        "password": "anothersecurepassword",
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)

    assert resp.status_code == status.HTTP_201_CREATED
    payload = resp.json()
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"

    # Verify user is created with optional fields as None
    result = await db.execute(select(User).where(User.username == "minimaluser"))
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.first_name is None
    assert created_user.last_name is None


@pytest.mark.asyncio
async def test_register_duplicate_username(
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """Test duplicate username returns 409."""
    client, db = auth_client

    # Create existing user
    await _create_existing_user(db, username="duplicateuser", email="first@test.com")

    registration_data = {
        "username": "duplicateuser",  # Same username
        "email": "different@test.com",  # Different email
        "password": "securepassword123",
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)

    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["detail"] == "Username or email already exists"


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_client: tuple[AsyncClient, AsyncSession]):
    """Test duplicate email returns 409."""
    client, db = auth_client

    # Create existing user
    await _create_existing_user(db, username="firstuser", email="duplicate@test.com")

    registration_data = {
        "username": "differentuser",  # Different username
        "email": "duplicate@test.com",  # Same email
        "password": "securepassword123",
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)

    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.json()["detail"] == "Username or email already exists"


@pytest.mark.asyncio
async def test_register_password_too_short(
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """Test password < 12 chars returns 400."""
    client, _ = auth_client

    # Test with 11 characters
    registration_data = {
        "username": "testuser",
        "email": "test@test.com",
        "password": "short11char",  # 11 characters
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Pydantic validation error for min_length constraint
    assert "detail" in resp.json()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "password",
    [
        "short",  # 5 characters
        "password10",  # 10 characters
        "password11",  # 11 characters
    ],
)
async def test_register_password_various_short_lengths(
    auth_client: tuple[AsyncClient, AsyncSession], password: str
):
    client, _ = auth_client

    registration_data = {
        "username": "testuser",
        "email": "test@test.com",
        "password": password,
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Pydantic validation error for min_length constraint
    assert "detail" in resp.json()


@pytest.mark.asyncio
async def test_register_token_grants_access(
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """Test returned token works on protected endpoint."""
    client, _ = auth_client

    registration_data = {
        "username": "tokenuser",
        "email": "token@test.com",
        "password": "securepassword123",
    }

    # Register user and get token
    resp = await client.post("/api/v1/auth/register", json=registration_data)
    assert resp.status_code == status.HTTP_201_CREATED

    token = resp.json()["access_token"]

    # Use token to access protected endpoint
    protected_resp = await client.get(
        "/api/v1/mealplans/weekly?start=2025-01-14",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Should not be unauthorized (token works)
    assert protected_resp.status_code != status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_register_invalid_email(auth_client: tuple[AsyncClient, AsyncSession]):
    """Test invalid email format returns 422."""
    client, _ = auth_client

    registration_data = {
        "username": "testuser",
        "email": "not-an-email",  # Invalid email format
        "password": "securepassword123",
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "username",
    [
        "ab",  # Too short (< 3 chars)
        "a" * 33,  # Too long (> 32 chars)
        "user@name",  # Contains invalid character (@)
        "user name",  # Contains space
        "user.name",  # Contains period
    ],
)
async def test_register_invalid_username_pattern(
    auth_client: tuple[AsyncClient, AsyncSession], username: str
):
    client, _ = auth_client

    registration_data = {
        "username": username,
        "email": "test@test.com",
        "password": "securepassword123",
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)

    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "username",
    [
        "abc",  # Minimum length (3 chars)
        "a" * 32,  # Maximum length (32 chars)
        "user_name",  # Contains underscore
        "user-name",  # Contains hyphen
        "user123",  # Contains numbers
        "User123",  # Contains uppercase
    ],
)
async def test_register_valid_username_patterns(
    auth_client: tuple[AsyncClient, AsyncSession], username: str
):
    client, _ = auth_client

    registration_data = {
        "username": username,
        "email": "valid@test.com",
        "password": "securepassword123",
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)

    # Should succeed (not 422)
    assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.asyncio
async def test_register_missing_required_fields(
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """Test missing username/email/password returns 422."""
    client, _ = auth_client

    # Missing username
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@test.com", "password": "securepassword123"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing email
    resp = await client.post(
        "/api/v1/auth/register",
        json={"username": "testuser", "password": "securepassword123"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing password
    resp = await client.post(
        "/api/v1/auth/register", json={"username": "testuser", "email": "test@test.com"}
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_register_email_normalization(
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """Test email is normalized to lowercase."""
    client, db = auth_client

    registration_data = {
        "username": "normalizeuser",
        "email": "UPPERCASE@TEST.COM",  # Uppercase email
        "password": "securepassword123",
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)
    assert resp.status_code == status.HTTP_201_CREATED

    # Verify email is stored in lowercase
    result = await db.execute(select(User).where(User.username == "normalizeuser"))
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.email == "uppercase@test.com"  # Should be lowercase


@pytest.mark.asyncio
async def test_register_password_exactly_12_chars(
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """Test password with exactly 12 characters is accepted."""
    client, _ = auth_client

    registration_data = {
        "username": "exactuser",
        "email": "exact@test.com",
        "password": "exactly12chr",  # Exactly 12 characters
    }

    resp = await client.post("/api/v1/auth/register", json=registration_data)

    assert resp.status_code == status.HTTP_201_CREATED
    payload = resp.json()
    assert payload["access_token"]
    assert payload["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_password_too_short_internal_validation_unit(
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """
    Unit-level test that directly invokes the register() endpoint function to
    cover the manual password-length check path (len(payload.password) < 12),
    which is bypassed by FastAPI/Pydantic validation in HTTP tests.

    This ensures coverage for the error handling branch that raises HTTP 400
    with detail 'Password too short'.
    """
    # Import locally to avoid modifying module-level imports and keep the test isolated
    from types import SimpleNamespace

    from fastapi import HTTPException, status  # type: ignore

    from api.v1.auth import register  # type: ignore

    _, db = auth_client  # We only need the DB session, not the client

    # Create a minimal payload-like object that bypasses Pydantic validation
    # so we can hit the manual password length branch inside the route function.
    payload = SimpleNamespace(
        username="unitshort",
        email="UNIT@EXAMPLE.COM",  # upper-case to also execute normalization code
        password="short",  # < 12 characters to trigger the manual 400 path
        first_name="Unit",
        last_name="Test",
    )

    with pytest.raises(HTTPException) as excinfo:
        await register(payload, db)

    assert excinfo.value.status_code == status.HTTP_400_BAD_REQUEST
    assert excinfo.value.detail == "Password too short"

    # Ensure no user was created in the database
    result = await db.execute(select(User).where(User.username == "unitshort"))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_register_duplicate_user_error_unit(
    monkeypatch: pytest.MonkeyPatch,
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """
    Unit-level test to force DuplicateUserError from create_user to cover the
    register() exception path (HTTP 409) explicitly.
    """
    from types import SimpleNamespace

    from fastapi import HTTPException, status  # type: ignore

    import api.v1.auth as auth_mod  # type: ignore
    from core.exceptions import DuplicateUserError  # type: ignore

    # Patch the dependencies in the module under test
    monkeypatch.setattr(auth_mod, "get_password_hash", lambda pw: "hashed_pw")

    async def _raise_duplicate(*args, **kwargs):
        raise DuplicateUserError()

    monkeypatch.setattr(auth_mod, "create_user", _raise_duplicate)

    _, db = auth_client

    payload = SimpleNamespace(
        username="dupeuser",
        email="dupe@EXAMPLE.COM",
        password="longenoughpassword",
        first_name=None,
        last_name=None,
    )

    with pytest.raises(HTTPException) as excinfo:
        await auth_mod.register(payload, db)

    assert excinfo.value.status_code == status.HTTP_409_CONFLICT
    assert excinfo.value.detail == "Username or email already exists"


@pytest.mark.asyncio
async def test_register_success_unit_token_path(
    monkeypatch: pytest.MonkeyPatch,
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """
    Unit-level success test that mocks create_user and create_access_token
    to ensure the token creation/return lines are covered in register().
    """
    import uuid
    from types import SimpleNamespace

    import api.v1.auth as auth_mod  # type: ignore

    # Patch hashing and token creation
    monkeypatch.setattr(auth_mod, "get_password_hash", lambda pw: "hashed_pw")
    monkeypatch.setattr(auth_mod, "create_access_token", lambda data: "unit-token")

    class _DummyUser:
        def __init__(self):
            self.id = uuid.uuid4()

    async def _fake_create_user(*args, **kwargs):
        return _DummyUser()

    monkeypatch.setattr(auth_mod, "create_user", _fake_create_user)

    _, db = auth_client
    payload = SimpleNamespace(
        username="unitok",
        email="UNITOK@EXAMPLE.COM",  # also exercises email normalization
        password="longenoughpassword",
        first_name=None,
        last_name=None,
    )

    token = await auth_mod.register(payload, db)
    assert token.access_token == "unit-token"
    assert token.token_type == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials_unit(
    monkeypatch: pytest.MonkeyPatch,
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """
    Unit-level test for login() invalid credentials path to cover lines 28-36
    in [api.v1.auth](apps/backend/src/api/v1/auth.py:1). Ensures 401 is raised.
    """
    from types import SimpleNamespace

    from fastapi import HTTPException, status  # type: ignore

    import api.v1.auth as auth_mod  # type: ignore

    # Force get_user_by_username to return no user
    async def _no_user(*args, **kwargs):
        return None

    monkeypatch.setattr(auth_mod, "get_user_by_username", _no_user)

    _, db = auth_client
    form = SimpleNamespace(username="nouser", password="badpass")

    with pytest.raises(HTTPException) as excinfo:
        await auth_mod.login(form, db)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Incorrect username or password"


@pytest.mark.asyncio
async def test_login_success_unit(
    monkeypatch: pytest.MonkeyPatch,
    auth_client: tuple[AsyncClient, AsyncSession],
):
    """
    Unit-level test for login() success path to cover token creation lines
    in [api.v1.auth](apps/backend/src/api/v1/auth.py:1). Returns a deterministic token.
    """
    import uuid
    from types import SimpleNamespace

    import api.v1.auth as auth_mod  # type: ignore

    # Deterministic token generation
    monkeypatch.setattr(
        auth_mod,
        "create_access_token",
        lambda data: "unit-login-token",
    )

    # Build a dummy user with a valid hashed password
    class _DummyUser:
        def __init__(self):
            self.id = uuid.uuid4()
            self.hashed_password = auth_mod.get_password_hash("goodpass")

    async def _user_ok(db, username: str):
        return _DummyUser()

    monkeypatch.setattr(auth_mod, "get_user_by_username", _user_ok)

    _, db = auth_client
    form = SimpleNamespace(username="dummy", password="goodpass")

    token = await auth_mod.login(form, db)
    assert token.access_token == "unit-login-token"
    assert token.token_type == "bearer"
