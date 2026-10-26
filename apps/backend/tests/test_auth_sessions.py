from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi import HTTPException, Response, status
from httpx import AsyncClient
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import api.v1.auth as auth_module
import core.security as security_module
import core.session as session_module
import dependencies.auth as dependency_auth_module
from core.config import get_settings
from core.security import generate_password_reset_token, get_password_hash
from core.session import SESSION_ABSOLUTE_TIMEOUT, SESSION_CONFIRMATION_WINDOW
from models.auth_sessions import AuthSession
from models.users import User
from schemas.auth import ResetPasswordRequest


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
    token = response.json()["access_token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    client.headers["X-Session-ID"] = claims["sid"]
    assert response.cookies.get(cookie_name(client))
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    return token


def cookie_name(client: AsyncClient) -> str:
    return f"pantrypilot_session_{client.headers['X-Session-ID']}"


@pytest.mark.parametrize(
    ("environment", "secure"), [("production", True), ("development", False)]
)
def test_refresh_cookie_security_flags(
    monkeypatch: pytest.MonkeyPatch, environment: str, secure: bool
) -> None:
    monkeypatch.setattr(get_settings(), "ENVIRONMENT", environment)
    response = Response()

    session_id = uuid4()
    auth_module._set_refresh_cookie(response, session_id, "browser-only-credential", 60)

    cookie = response.headers["set-cookie"].lower()
    assert ("; secure" in cookie) is secure
    assert "; httponly" in cookie
    assert "; samesite=lax" in cookie
    assert "; path=/api/v1/auth" in cookie
    auth_module._delete_refresh_cookie(response, session_id)
    deletion = response.headers.getlist("set-cookie")[-1].lower()
    assert cookie.split("=", 1)[0] == deletion.split("=", 1)[0]
    assert ("; secure" in deletion) is secure
    assert "; samesite=lax" in deletion


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
    original_cookie = client.cookies.get(cookie_name(client))
    assert original_cookie is not None

    for interval in range(3):
        FrozenDateTime.current += timedelta(minutes=20) + (
            timedelta(seconds=1) if interval == 2 else timedelta()
        )
        response = await client.post(
            "/api/v1/auth/refresh", json={"extend_session": True}
        )
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
                json={"extend_session": True},
                headers={"Cookie": f"{cookie_name(client)}={original_cookie}"},
            )
            assert concurrent_refresh.status_code == status.HTTP_200_OK
            assert concurrent_refresh.headers["set-cookie"].split("=", 1)[1].split(
                ";", 1
            )[0] == (client.cookies.get(cookie_name(client)))

    session_age = FrozenDateTime.current - auth_session.created_at.replace(tzinfo=UTC)
    assert session_age > timedelta(hours=1)
    assert int(FrozenDateTime.current.timestamp()) > claims["exp"]


@pytest.mark.asyncio
async def test_refresh_does_not_count_as_activity_and_expires_at_confirmation_boundary(
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
        FrozenDateTime.current - SESSION_CONFIRMATION_WINDOW + timedelta(seconds=1)
    )
    await db.commit()
    silent_refresh = await client.post(
        "/api/v1/auth/refresh", json={"extend_session": False}
    )
    assert silent_refresh.status_code == status.HTTP_200_OK
    await db.refresh(auth_session)
    assert auth_session.last_activity_at.replace(tzinfo=UTC) == (
        FrozenDateTime.current - SESSION_CONFIRMATION_WINDOW + timedelta(seconds=1)
    )

    FrozenDateTime.current += timedelta(seconds=1)
    expired_refresh = await client.post(
        "/api/v1/auth/refresh", json={"extend_session": True}
    )
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
    response = await client.post("/api/v1/auth/refresh", json={"extend_session": True})

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
    refresh = await client.post("/api/v1/auth/refresh", json={"extend_session": True})
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
    old_cookie = client.cookies.get(cookie_name(client))

    rotated = await client.post("/api/v1/auth/refresh", json={"extend_session": True})
    assert rotated.status_code == status.HTTP_200_OK
    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Cookie": f"{cookie_name(client)}={old_cookie}"},
    )
    assert logout.status_code == status.HTTP_204_NO_CONTENT
    refresh = await client.post("/api/v1/auth/refresh", json={"extend_session": True})
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
    previous_cookie = client.cookies.get(cookie_name(client))
    assert previous_cookie is not None

    rotated = await client.post("/api/v1/auth/refresh", json={"extend_session": True})
    assert rotated.status_code == status.HTTP_200_OK
    FrozenDateTime.current += timedelta(seconds=31)
    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"extend_session": False},
        headers={"Cookie": f"{cookie_name(client)}={previous_cookie}"},
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
    original_cookie = client.cookies.get(cookie_name(client))

    await client.post("/api/v1/auth/refresh", json={"extend_session": True})
    rotated_cookie = client.cookies.get(cookie_name(client))
    assert rotated_cookie != original_cookie

    FrozenDateTime.current += timedelta(seconds=29)
    response = await client.post("/api/v1/auth/refresh", json={"extend_session": True})
    assert response.status_code == status.HTTP_200_OK
    assert client.cookies.get(cookie_name(client)) == rotated_cookie

    FrozenDateTime.current += timedelta(seconds=2)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"extend_session": True},
        headers={"Cookie": f"{cookie_name(client)}={rotated_cookie}"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert client.cookies.get(cookie_name(client)) != rotated_cookie

    # The older generation does not gain time from a later rotation.
    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"extend_session": False},
        headers={"Cookie": f"{cookie_name(client)}={original_cookie}"},
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
@pytest.mark.parametrize("boundary", ["confirmation", "absolute"])
async def test_protected_action_requires_sign_in_at_session_boundary(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
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
    if boundary == "confirmation":
        auth_session.last_activity_at = (
            FrozenDateTime.current - SESSION_CONFIRMATION_WINDOW
        )
    else:
        auth_session.created_at = FrozenDateTime.current - SESSION_ABSOLUTE_TIMEOUT
    await db.commit()

    response = await client.get(
        "/api/v1/mealplans/weekly?start=2026-10-18",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "confirmation" in response.json()["detail"]
    await db.refresh(auth_session)
    assert auth_session.revoked_at is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "concurrent_result", ["renewed", "revoked", "deleted", "expired"]
)
async def test_suspected_expiry_reloads_locked_state_before_revoking(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
    monkeypatch: pytest.MonkeyPatch,
    concurrent_result: str,
):
    client, db = auth_client
    user = await create_user(db)
    token = await login(client, user)
    claims = jwt.decode(
        token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM]
    )
    session_id = UUID(claims["sid"])
    auth_session = await db.get(AuthSession, session_id)
    assert auth_session is not None
    auth_session.last_activity_at = FrozenDateTime.current - SESSION_CONFIRMATION_WINDOW
    await db.commit()
    original_scalar = db.scalar
    reads = 0

    async def racing_scalar(statement):
        nonlocal reads
        reads += 1
        if reads == 2:
            assert statement._for_update_arg is not None
            assert statement.get_execution_options()["populate_existing"] is True
        result = await original_scalar(statement)
        if reads == 1:
            if concurrent_result == "deleted":
                change = delete(AuthSession).where(AuthSession.id == session_id)
            else:
                values = {"last_activity_at": FrozenDateTime.current}
                if concurrent_result == "revoked":
                    values["revoked_at"] = FrozenDateTime.current
                if concurrent_result == "expired":
                    values["last_activity_at"] -= SESSION_CONFIRMATION_WINDOW
                change = (
                    update(AuthSession)
                    .where(AuthSession.id == session_id)
                    .values(**values)
                )
            # Simulate a newly committed row without updating the cached ORM object.
            await db.execute(change.execution_options(synchronize_session=False))
        return result

    async def get_user_after_unlock(_db, user_id):
        assert not db.in_transaction()
        assert user_id == user.id
        return user

    monkeypatch.setattr(db, "scalar", racing_scalar)
    monkeypatch.setattr(dependency_auth_module, "get_user_by_id", get_user_after_unlock)

    if concurrent_result == "renewed":
        result = await dependency_auth_module.get_current_user(db, token)
        assert result is user
        assert auth_session.revoked_at is None
        assert (
            auth_session.last_activity_at.replace(tzinfo=UTC) == FrozenDateTime.current
        )
    else:
        with pytest.raises(HTTPException) as exc:
            await dependency_auth_module.get_current_user(db, token)
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert not db.in_transaction()
    assert reads == 2


@pytest.mark.asyncio
async def test_explicit_confirmation_extends_one_hour_but_not_past_absolute_limit(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db = auth_client
    assert (
        type(get_settings()).model_fields["ACCESS_TOKEN_EXPIRE_MINUTES"].default == 15
    )
    monkeypatch.setattr(get_settings(), "ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    user = await create_user(db)
    token = await login(client, user)
    initial = jwt.decode(token, options={"verify_signature": False})
    assert initial["exp"] - int(FrozenDateTime.current.timestamp()) == 15 * 60
    assert initial["session_exp"] - int(FrozenDateTime.current.timestamp()) == 3600

    FrozenDateTime.current += timedelta(minutes=55)
    silent = await client.post("/api/v1/auth/refresh", json={})
    silent_claims = jwt.decode(
        silent.json()["access_token"], options={"verify_signature": False}
    )
    assert silent_claims["session_exp"] == initial["session_exp"]
    confirmation = await client.post(
        "/api/v1/auth/refresh", json={"extend_session": True}
    )
    confirmed = jwt.decode(
        confirmation.json()["access_token"], options={"verify_signature": False}
    )
    assert confirmed["session_exp"] == int(
        (FrozenDateTime.current + timedelta(hours=1)).timestamp()
    )
    session = await db.get(AuthSession, UUID(initial["sid"]))
    assert session is not None
    FrozenDateTime.current = FrozenDateTime.fromtimestamp(
        initial["absolute_exp"] - 60, UTC
    )
    session.last_activity_at = FrozenDateTime.current
    await db.commit()

    near_cap = await client.post("/api/v1/auth/refresh", json={"extend_session": True})
    cap_claims = jwt.decode(
        near_cap.json()["access_token"], options={"verify_signature": False}
    )
    assert cap_claims["session_exp"] == cap_claims["absolute_exp"]
    assert cap_claims["absolute_exp"] == initial["absolute_exp"]


@pytest.mark.asyncio
@pytest.mark.parametrize("old_response", ["refresh", "expired", "logout"])
async def test_delayed_session_a_cookie_cannot_replace_or_clear_session_b(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
    old_response: str,
) -> None:
    client, db = auth_client
    user = await create_user(db)
    await login(client, user)
    session_a = client.headers["X-Session-ID"]
    name_a = cookie_name(client)
    if old_response == "expired":
        session = await db.get(AuthSession, UUID(session_a))
        assert session is not None
        session.revoked_at = FrozenDateTime.current
        await db.commit()
    response_a = await client.post(
        f"/api/v1/auth/{'logout' if old_response == 'logout' else 'refresh'}",
        json={} if old_response != "logout" else None,
    )
    assert (
        response_a.status_code
        == {"refresh": 200, "expired": 401, "logout": 204}[old_response]
    )
    await login(client, user)
    name_b = cookie_name(client)
    cookie_b = client.cookies.get(name_b)
    assert name_b != name_a

    # Deliver A's Set-Cookie after B's login, as a browser would.
    client.cookies.extract_cookies(response_a)

    assert client.cookies.get(name_b) == cookie_b
    assert name_b not in response_a.headers["set-cookie"]
    renewed_b = await client.post("/api/v1/auth/refresh", json={})
    assert renewed_b.status_code == 200
    claims_b = jwt.decode(
        renewed_b.json()["access_token"], options={"verify_signature": False}
    )
    assert claims_b["sid"] == client.headers["X-Session-ID"]


@pytest.mark.asyncio
async def test_session_selector_and_origin_do_not_fall_back_to_another_cookie(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
) -> None:
    client, db = auth_client
    await login(client, await create_user(db))
    name = cookie_name(client)
    credential = client.cookies.get(name)

    unknown = await client.post(
        "/api/v1/auth/refresh", json={}, headers={"X-Session-ID": str(uuid4())}
    )
    assert unknown.status_code == 401
    assert name not in unknown.headers["set-cookie"]
    assert client.cookies.get(name) == credential
    forbidden = await client.post(
        "/api/v1/auth/refresh",
        json={"extend_session": True},
        headers={"Origin": "https://untrusted.example"},
    )
    assert forbidden.status_code == 403
    assert "set-cookie" not in forbidden.headers
    client.headers.pop("X-Session-ID")
    missing = await client.post("/api/v1/auth/refresh", json={})
    assert missing.status_code == 422
    assert "set-cookie" not in missing.headers


@pytest.mark.asyncio
async def test_given_account_sessions_when_password_reset_then_all_are_revoked(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
) -> None:
    client, db = auth_client
    user = await create_user(db)
    tokens = [await login(client, user), await login(client, user)]
    other = User(
        id=uuid4(),
        username="othercook",
        email="othercook@example.test",
        hashed_password=get_password_hash("long-secure-password"),
        is_verified=True,
    )
    db.add(other)
    await db.commit()
    other_token = await login(client, other)

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": generate_password_reset_token(user.email),
            "new_password": "replacement-secure-password",
        },
    )

    assert response.status_code == 200
    for token in tokens:
        claims = jwt.decode(token, options={"verify_signature": False})
        denied = await client.post(
            "/api/v1/auth/refresh",
            json={"extend_session": True},
            headers={"X-Session-ID": claims["sid"]},
        )
        assert denied.status_code == 401
        with pytest.raises(HTTPException) as exc:
            await dependency_auth_module.get_current_user(db, token)
        assert exc.value.status_code == 401
    assert await dependency_auth_module.get_current_user(db, other_token) is other
    assert (await client.post("/api/v1/auth/refresh", json={})).status_code == 200
    old_login = await client.post(
        "/api/v1/auth/login",
        data={"username": user.username, "password": "long-secure-password"},
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login",
        data={"username": user.username, "password": "replacement-secure-password"},
    )
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_given_invalid_reset_when_rejected_then_session_remains_usable(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
) -> None:
    client, db = auth_client
    await login(client, await create_user(db))

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "invalid", "new_password": "replacement-secure-password"},
    )

    assert response.status_code == 400
    assert (await client.post("/api/v1/auth/refresh", json={})).status_code == 200


@pytest.mark.asyncio
async def test_given_reset_commit_failure_then_password_and_revocation_roll_back(
    auth_client: tuple[AsyncClient, AsyncSession],
    frozen_session_clock: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db = auth_client
    user = await create_user(db)
    token = await login(client, user)
    session_id = UUID(jwt.decode(token, options={"verify_signature": False})["sid"])
    original_hash = user.hashed_password
    payload = ResetPasswordRequest(
        token=generate_password_reset_token(user.email),
        new_password="replacement-secure-password",
    )

    async def failing_commit() -> None:
        await db.flush()
        raise SQLAlchemyError("Simulated failed commit")

    with monkeypatch.context() as patch:
        patch.setattr(db, "commit", failing_commit)
        with pytest.raises(SQLAlchemyError, match="Simulated failed commit"):
            await auth_module.reset_password(payload, db)

    await db.refresh(user)
    session = await db.get(AuthSession, session_id)
    assert user.hashed_password == original_hash
    assert session is not None and session.revoked_at is None
    assert (await client.post("/api/v1/auth/refresh", json={})).status_code == 200
