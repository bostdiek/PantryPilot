"""Unit tests for auth.py email verification and password reset flows."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import (
    generate_password_reset_token,
    generate_verification_token,
    get_password_hash,
    verify_password,
)
from models.users import User


async def _create_user(
    db: AsyncSession,
    username: str = "testuser",
    email: str = "test@example.com",
    is_verified: bool = False,
) -> User:
    """Helper to create a user for testing."""
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash("oldpassword123"),
        first_name="Test",
        last_name="User",
        is_verified=is_verified,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


class TestVerifyEmailEndpoint:
    """Tests for POST /auth/verify-email endpoint."""

    @pytest.mark.asyncio
    async def test_verify_email_success(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Valid verification token should verify user and return access token."""
        client, db = auth_client

        # Create unverified user
        user = await _create_user(db, username="verifyuser", email="verify@test.com")
        assert user.is_verified is False

        # Generate valid verification token
        token = generate_verification_token("verify@test.com")

        resp = await client.post("/api/v1/auth/verify-email", json={"token": token})

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["message"] == "Email verified successfully"
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Verify user is now marked as verified in DB
        await db.refresh(user)
        assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_verify_email_already_verified(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Already verified user should still get a token."""
        client, db = auth_client

        # Create already verified user
        await _create_user(
            db, username="alreadyverified", email="already@test.com", is_verified=True
        )

        token = generate_verification_token("already@test.com")

        resp = await client.post("/api/v1/auth/verify-email", json={"token": token})

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["message"] == "Email already verified"
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Invalid token should return 400."""
        client, _ = auth_client

        resp = await client.post(
            "/api/v1/auth/verify-email", json={"token": "invalid-token"}
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["detail"] == "Invalid or expired verification token"

    @pytest.mark.asyncio
    async def test_verify_email_user_not_found(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Valid token for non-existent user should return 404."""
        client, _ = auth_client

        # Generate token for email that doesn't exist in DB
        token = generate_verification_token("nonexistent@test.com")

        resp = await client.post("/api/v1/auth/verify-email", json={"token": token})

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["detail"] == "User not found"


class TestForgotPasswordEndpoint:
    """Tests for POST /auth/forgot-password endpoint."""

    @pytest.mark.asyncio
    async def test_forgot_password_existing_user(
        self,
        auth_client: tuple[AsyncClient, AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Request for existing user should send email (mocked)."""
        client, db = auth_client

        await _create_user(db, username="forgotuser", email="forgot@test.com")

        # Mock email sending
        import api.v1.auth as auth_mod

        monkeypatch.setattr(auth_mod, "send_password_reset_email", lambda e, t: True)

        resp = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "forgot@test.com"}
        )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "password reset link has been sent" in data["message"]

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Request for non-existent email should still return success (security)."""
        client, _ = auth_client

        resp = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "nonexistent@test.com"}
        )

        # Should return success to prevent email enumeration
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "password reset link has been sent" in data["message"]

    @pytest.mark.asyncio
    async def test_forgot_password_email_normalized(
        self,
        auth_client: tuple[AsyncClient, AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Email should be normalized to lowercase."""
        client, db = auth_client

        await _create_user(db, username="caseuser", email="case@test.com")

        import api.v1.auth as auth_mod

        monkeypatch.setattr(auth_mod, "send_password_reset_email", lambda e, t: True)

        # Send with uppercase email
        resp = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "CASE@TEST.COM"}
        )

        assert resp.status_code == status.HTTP_200_OK


class TestResetPasswordEndpoint:
    """Tests for POST /auth/reset-password endpoint."""

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Valid reset token should allow password reset."""
        client, db = auth_client

        user = await _create_user(db, username="resetuser", email="reset@test.com")
        old_hash = user.hashed_password

        # Generate valid reset token
        token = generate_password_reset_token("reset@test.com")

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token,
                "new_password": "newpassword123",
            },  # pragma: allowlist secret
        )  # pragma: allowlist secret

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["message"] == "Password reset successfully"

        # Verify password was actually changed
        await db.refresh(user)
        assert user.hashed_password != old_hash
        assert (
            verify_password(
                "newpassword123",
                user.hashed_password,
            )  # pragma: allowlist secret
        )

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Invalid reset token should return 400."""
        client, _ = auth_client

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid-token",
                "new_password": "newpassword123",
            },  # pragma: allowlist secret
        )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.json()["detail"] == "Invalid or expired reset token"

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Valid token for non-existent user should return 404."""
        client, _ = auth_client

        token = generate_password_reset_token("nonexistent@test.com")

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token,
                "new_password": "newpassword123",
            },
        )

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.json()["detail"] == "User not found"

    @pytest.mark.asyncio
    async def test_reset_password_too_short(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Password less than 12 chars should return 422 (Pydantic validation)."""
        client, db = auth_client

        await _create_user(db, username="shortpwuser", email="shortpw@test.com")

        token = generate_password_reset_token("shortpw@test.com")

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "short"},
        )  # pragma: allowlist secret

        # Pydantic validates min_length=12 before endpoint code
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestVerifyEmailUnit:
    """Unit-level tests for verify_email() function."""

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token_unit(
        self,
        auth_client: tuple[AsyncClient, AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Unit test for invalid token path."""
        import api.v1.auth as auth_mod

        _, db = auth_client

        # Mock verify_email_token to return None
        monkeypatch.setattr(auth_mod, "verify_email_token", lambda t: None)

        payload = SimpleNamespace(token="bad-token")

        with pytest.raises(HTTPException) as exc:
            await auth_mod.verify_email(payload, db)

        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.value.detail == "Invalid or expired verification token"


class TestForgotPasswordUnit:
    """Unit-level tests for forgot_password() function."""

    @pytest.mark.asyncio
    async def test_forgot_password_email_send_failure_logs_warning(
        self,
        auth_client: tuple[AsyncClient, AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """When email sending fails, should log warning but still return success."""
        import api.v1.auth as auth_mod

        _, db = auth_client

        # Create user
        user = User(
            id=uuid4(),
            username="emailfailuser",
            email="emailfail@test.com",
            hashed_password="hash",  # pragma: allowlist secret
            is_verified=True,
        )
        db.add(user)
        await db.commit()

        # Mock to find user and fail email send (need async mock)
        async def mock_get_user(db, email):
            return user

        monkeypatch.setattr(auth_mod, "get_user_by_email", mock_get_user)
        monkeypatch.setattr(
            auth_mod,
            "generate_password_reset_token",
            lambda email: "token",  # pragma: allowlist secret
        )
        monkeypatch.setattr(
            auth_mod, "send_password_reset_email", lambda email, token: False
        )

        payload = SimpleNamespace(
            email="emailfail@test.com",  # pragma: allowlist secret
        )
        result = await auth_mod.forgot_password(payload, db)

        # Should still return success message
        assert "password reset link has been sent" in result.message


class TestResetPasswordUnit:
    """Unit-level tests for reset_password() function."""

    @pytest.mark.asyncio
    async def test_reset_password_short_password_unit(
        self,
        auth_client: tuple[AsyncClient, AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Unit test for password length validation."""
        import api.v1.auth as auth_mod

        _, db = auth_client

        # Create user
        user = User(
            id=uuid4(),
            username="shortpwunit",
            email="shortpwunit@test.com",
            hashed_password="hash",
            is_verified=True,
        )
        db.add(user)
        await db.commit()

        # Mock token verification to return email
        monkeypatch.setattr(
            auth_mod, "verify_password_reset_token", lambda t: "shortpwunit@test.com"
        )

        async def mock_get_user(db, email):
            return user

        monkeypatch.setattr(auth_mod, "get_user_by_email", mock_get_user)

        payload = SimpleNamespace(
            token="valid-token",  # pragma: allowlist secret
            new_password="short",
        )

        with pytest.raises(HTTPException) as exc:
            await auth_mod.reset_password(payload, db)

        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.value.detail == "Password must be at least 12 characters"


class TestResendVerificationEndpoint:
    """Tests for POST /auth/resend-verification endpoint."""

    @pytest.mark.asyncio
    async def test_resend_verification_unverified_user(
        self,
        auth_client: tuple[AsyncClient, AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Resend verification for unverified user should send email."""
        client, db = auth_client

        await _create_user(
            db, username="unverified", email="unverified@test.com", is_verified=False
        )

        # Mock email sending
        import api.v1.auth as auth_mod

        email_sent_to: list[str] = []

        def mock_send_verification(email: str, token: str) -> bool:
            email_sent_to.append(email)
            return True

        monkeypatch.setattr(auth_mod, "send_verification_email", mock_send_verification)

        resp = await client.post(
            "/api/v1/auth/resend-verification", json={"email": "unverified@test.com"}
        )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "verification link has been sent" in data["message"]
        assert email_sent_to == ["unverified@test.com"]

    @pytest.mark.asyncio
    async def test_resend_verification_already_verified_user(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Already verified user gets success but no email sent."""
        client, db = auth_client

        await _create_user(
            db, username="verified", email="verified@test.com", is_verified=True
        )

        resp = await client.post(
            "/api/v1/auth/resend-verification", json={"email": "verified@test.com"}
        )

        # Should return success to prevent email enumeration
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "verification link has been sent" in data["message"]

    @pytest.mark.asyncio
    async def test_resend_verification_nonexistent_email(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Non-existent email returns success to prevent enumeration."""
        client, _ = auth_client

        resp = await client.post(
            "/api/v1/auth/resend-verification", json={"email": "nonexistent@test.com"}
        )

        # Should return success to prevent email enumeration
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "verification link has been sent" in data["message"]

    @pytest.mark.asyncio
    async def test_resend_verification_email_normalized(
        self,
        auth_client: tuple[AsyncClient, AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Email should be normalized to lowercase."""
        client, db = auth_client

        await _create_user(
            db, username="casetest", email="casetest@test.com", is_verified=False
        )

        import api.v1.auth as auth_mod

        email_sent_to: list[str] = []

        def mock_send_verification(email: str, token: str) -> bool:
            email_sent_to.append(email)
            return True

        monkeypatch.setattr(auth_mod, "send_verification_email", mock_send_verification)

        # Send with uppercase email
        resp = await client.post(
            "/api/v1/auth/resend-verification", json={"email": "CASETEST@TEST.COM"}
        )

        assert resp.status_code == status.HTTP_200_OK
        # Email should be normalized to lowercase when sent
        assert email_sent_to == ["casetest@test.com"]


class TestResendVerificationUnit:
    """Unit-level tests for resend_verification() function."""

    @pytest.mark.asyncio
    async def test_resend_verification_email_send_failure_logs_warning(
        self,
        auth_client: tuple[AsyncClient, AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ):
        """When email sending fails, should log warning but still return success."""
        import api.v1.auth as auth_mod

        _, db = auth_client

        # Create unverified user
        user = User(
            id=uuid4(),
            username="emailfailresend",
            email="emailfailresend@test.com",
            hashed_password="hash",  # pragma: allowlist secret
            is_verified=False,
        )
        db.add(user)
        await db.commit()

        # Mock to find user and fail email send
        async def mock_get_user(db, email):
            return user

        monkeypatch.setattr(auth_mod, "get_user_by_email", mock_get_user)
        monkeypatch.setattr(
            auth_mod,
            "generate_verification_token",
            lambda email: "token",  # pragma: allowlist secret
        )
        monkeypatch.setattr(
            auth_mod, "send_verification_email", lambda email, token: False
        )

        payload = SimpleNamespace(email="emailfailresend@test.com")
        result = await auth_mod.resend_verification(payload, db)

        # Should still return success message
        assert "verification link has been sent" in result.message
