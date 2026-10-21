from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import Response, status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import api.v1.auth as auth_module
import core.security as security_module
import core.session as session_module
import dependencies.auth as dependency_auth_module
from core.config import get_settings
from core.session import SESSION_ABSOLUTE_TIMEOUT, SESSION_IDLE_TIMEOUT
from models.auth_sessions import AuthSession
from models.users import User


class FrozenDateTime(datetime):
    current = datetime(2026, 10, 21, 12, tzinfo=UTC)

    @classmethod
    def now(cls, tz=None):
        return cls.current.astimezone(tz) if tz else cls.current


async def create_user(db: AsyncSession) -> User:
    from core.security import get_password_hash

    user = User(
        id=uuid4(),
        username="activecook",
        email="activecook@example.test",
        hashed_password=get_password_hash("long-secure-password"),
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
def frozen_session_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(session_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(security_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(dependency_auth_module, "datetime", FrozenDateTime)
    monkeypatch.setattr(jwt.api_jwt, "datetime", FrozenDateTime)
    FrozenDateTime.current = FrozenDateTime(2026, 10, 21, 12, tzinfo=UTC)


async def login(client: AsyncClient, user: User) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": user.username, "password": "long-secure-password"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.cookies.get("pantrypilot_session")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    return response.json()["access_token"]


@pytest.mark.parametrize(
    ("environment", "secure"), [("production", True), ("development", False)]
)
def test_refresh_cookie_security_flags(
    monkeypatch: pytest.MonkeyPatch, environment: str, secure: bool
) -> None:
    monkeypatch.setattr(get_settings(), "ENVIRONMENT", environment)
    response = Response()

    auth_module._set_refresh_cookie(response, "browser-only-credential", 60)

    cookie = response.headers["set-cookie"].lower()
    assert ("; secure" in cookie) is secure
    assert "; httponly" in cookie
    assert "; samesite=lax" in cookie
    assert "; path=/api/v1/auth" in cookie


@pytest.mark.asyncio
async def test_active_session_renews_across_multiple_access_token_lifetimes(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
):
    client, db = auth_client
    user = await create_user(db)
    first_token = await login(client, user)
    claims = jwt.decode(
        first_token,
        get_settings().SECRET_KEY,
        algorithms=[get_settings().ALGORITHM],
        options={"verify_exp": False},
    )
    auth_session = await db.get(AuthSession, UUID(claims["sid"]))
    assert auth_session is not None
    original_cookie = client.cookies.get("pantrypilot_session")
    assert original_cookie is not None

    for interval in range(3):
        FrozenDateTime.current += timedelta(minutes=20) + (
            timedelta(seconds=1) if interval == 2 else timedelta()
        )
        response = await client.post("/api/v1/auth/refresh", json={"activity": True})
        assert response.status_code == status.HTTP_200_OK
        access_token = response.json()["access_token"]
        decoded = jwt.decode(
            access_token,
            get_settings().SECRET_KEY,
            algorithms=[get_settings().ALGORITHM],
            options={"verify_exp": False},
        )
        assert decoded["sid"] == claims["sid"]
        if interval == 0:
            concurrent_refresh = await client.post(
                "/api/v1/auth/refresh",
                json={"activity": True},
                headers={"Cookie": f"pantrypilot_session={original_cookie}"},
            )
            assert concurrent_refresh.status_code == status.HTTP_200_OK
            assert concurrent_refresh.headers["set-cookie"].split("=", 1)[1].split(
                ";", 1
            )[0] == (client.cookies.get("pantrypilot_session"))

    session_age = FrozenDateTime.current - auth_session.created_at.replace(tzinfo=UTC)
    assert session_age > timedelta(hours=1)
    assert int(FrozenDateTime.current.timestamp()) > claims["exp"]


@pytest.mark.asyncio
async def test_refresh_does_not_count_as_activity_and_expires_at_idle_boundary(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
):
    client, db = auth_client
    user = await create_user(db)
    token = await login(client, user)
    claims = jwt.decode(
        token,
        get_settings().SECRET_KEY,
        algorithms=[get_settings().ALGORITHM],
        options={"verify_exp": False},
    )
    auth_session = await db.get(AuthSession, UUID(claims["sid"]))
    assert auth_session is not None

    auth_session.last_activity_at = (
        FrozenDateTime.current - SESSION_IDLE_TIMEOUT + timedelta(seconds=1)
    )
    await db.commit()
    silent_refresh = await client.post("/api/v1/auth/refresh", json={"activity": False})
    assert silent_refresh.status_code == status.HTTP_200_OK
    await db.refresh(auth_session)
    assert auth_session.last_activity_at.replace(tzinfo=UTC) == (
        FrozenDateTime.current - SESSION_IDLE_TIMEOUT + timedelta(seconds=1)
    )

    FrozenDateTime.current += timedelta(seconds=1)
    expired_refresh = await client.post("/api/v1/auth/refresh", json={"activity": True})
    assert expired_refresh.status_code == status.HTTP_401_UNAUTHORIZED
    await db.refresh(auth_session)
    assert auth_session.revoked_at is not None


@pytest.mark.asyncio
async def test_absolute_limit_is_enforced_at_exact_boundary(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
):
    client, db = auth_client
    user = await create_user(db)
    token = await login(client, user)
    claims = jwt.decode(
        token,
        get_settings().SECRET_KEY,
        algorithms=[get_settings().ALGORITHM],
        options={"verify_exp": False},
    )
    auth_session = await db.get(AuthSession, UUID(claims["sid"]))
    assert auth_session is not None

    auth_session.created_at = FrozenDateTime.current - SESSION_ABSOLUTE_TIMEOUT
    auth_session.last_activity_at = FrozenDateTime.current
    await db.commit()
    response = await client.post("/api/v1/auth/refresh", json={"activity": True})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    await db.refresh(auth_session)
    assert auth_session.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_revokes_session_and_blocks_refresh(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
):
    client, db = auth_client
    user = await create_user(db)
    token = await login(client, user)
    claims = jwt.decode(
        token,
        get_settings().SECRET_KEY,
        algorithms=[get_settings().ALGORITHM],
        options={"verify_exp": False},
    )

    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    refresh = await client.post("/api/v1/auth/refresh", json={"activity": True})
    assert refresh.status_code == status.HTTP_401_UNAUTHORIZED

    auth_session = await db.scalar(
        select(AuthSession).where(AuthSession.id == UUID(claims["sid"]))
    )
    assert auth_session is not None
    assert auth_session.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_during_refresh_revokes_even_a_pending_old_cookie(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
):
    client, db = auth_client
    user = await create_user(db)
    token = await login(client, user)
    claims = jwt.decode(
        token,
        get_settings().SECRET_KEY,
        algorithms=[get_settings().ALGORITHM],
        options={"verify_exp": False},
    )
    old_cookie = client.cookies.get("pantrypilot_session")

    rotated = await client.post("/api/v1/auth/refresh", json={"activity": True})
    assert rotated.status_code == status.HTTP_200_OK
    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Cookie": f"pantrypilot_session={old_cookie}"},
    )
    assert logout.status_code == status.HTTP_204_NO_CONTENT
    refresh = await client.post("/api/v1/auth/refresh", json={"activity": True})
    assert refresh.status_code == status.HTTP_401_UNAUTHORIZED

    auth_session = await db.get(AuthSession, UUID(claims["sid"]))
    assert auth_session is not None
    assert auth_session.revoked_at is not None


@pytest.mark.asyncio
async def test_reuse_of_rotated_credential_after_grace_revokes_session(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
):
    client, db = auth_client
    user = await create_user(db)
    token = await login(client, user)
    claims = jwt.decode(
        token,
        get_settings().SECRET_KEY,
        algorithms=[get_settings().ALGORITHM],
        options={"verify_exp": False},
    )
    previous_cookie = client.cookies.get("pantrypilot_session")
    assert previous_cookie is not None

    rotated = await client.post("/api/v1/auth/refresh", json={"activity": True})
    assert rotated.status_code == status.HTTP_200_OK
    FrozenDateTime.current += timedelta(seconds=31)
    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"activity": False},
        headers={"Cookie": f"pantrypilot_session={previous_cookie}"},
    )

    assert replay.status_code == status.HTTP_401_UNAUTHORIZED
    auth_session = await db.get(AuthSession, UUID(claims["sid"]))
    assert auth_session is not None
    assert auth_session.revoked_at is not None


@pytest.mark.asyncio
async def test_refresh_during_overlap_does_not_rotate_again(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
):
    client, db = auth_client
    user = await create_user(db)
    await login(client, user)
    original_cookie = client.cookies.get("pantrypilot_session")

    await client.post("/api/v1/auth/refresh", json={"activity": True})
    rotated_cookie = client.cookies.get("pantrypilot_session")
    assert rotated_cookie != original_cookie

    FrozenDateTime.current += timedelta(seconds=29)
    response = await client.post("/api/v1/auth/refresh", json={"activity": True})
    assert response.status_code == status.HTTP_200_OK
    assert client.cookies.get("pantrypilot_session") == rotated_cookie

    FrozenDateTime.current += timedelta(seconds=2)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"activity": True},
        headers={"Cookie": f"pantrypilot_session={rotated_cookie}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert client.cookies.get("pantrypilot_session") != rotated_cookie

    # The older generation does not gain time from a later rotation.
    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"activity": False},
        headers={"Cookie": f"pantrypilot_session={original_cookie}"},
    )
    assert replay.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_frozen_clock_preserves_jwt_expiry_validation(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
):
    client, db = auth_client
    user = await create_user(db)
    token = await login(client, user)
    claims = jwt.decode(
        token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM]
    )

    FrozenDateTime.current = FrozenDateTime.fromtimestamp(claims["exp"], UTC)
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(
            token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM]
        )


@pytest.mark.asyncio
async def test_protected_action_requires_sign_in_at_idle_boundary(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
    monkeypatch: pytest.MonkeyPatch,
):
    client, db = auth_client
    monkeypatch.setattr(get_settings(), "ACCESS_TOKEN_EXPIRE_MINUTES", 120)
    user = await create_user(db)
    token = await login(client, user)
    claims = jwt.decode(
        token,
        get_settings().SECRET_KEY,
        algorithms=[get_settings().ALGORITHM],
        options={"verify_exp": False},
    )
    auth_session = await db.get(AuthSession, UUID(claims["sid"]))
    assert auth_session is not None
    auth_session.last_activity_at = FrozenDateTime.current - SESSION_IDLE_TIMEOUT
    await db.commit()

    response = await client.get(
        "/api/v1/mealplans/weekly?start=2026-10-18",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "inactivity" in response.json()["detail"]
    await db.refresh(auth_session)
    assert auth_session.revoked_at is not None
