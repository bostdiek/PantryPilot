"""Unit tests for core/security.py to cover token generation and verification."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from itsdangerous import BadSignature, SignatureExpired

from core.security import (
    EMAIL_VERIFICATION_EXPIRATION,
    PASSWORD_RESET_EXPIRATION,
    create_access_token,
    create_draft_token,
    decode_draft_token,
    decode_token,
    generate_password_reset_token,
    generate_verification_token,
    get_password_hash,
    verify_email_token,
    verify_password,
    verify_password_reset_token,
)


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_get_password_hash_returns_hash(self):
        """Password hash should not equal the plaintext."""
        password = "securepassword123"  # pragma: allowlist secret
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 20  # Argon2 hashes are fairly long

    def test_verify_password_correct(self):
        """Correct password should verify."""
        password = "securepassword123"  # pragma: allowlist secret
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Incorrect password should not verify."""
        hashed = get_password_hash("correctpassword")  # pragma: allowlist secret
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_malformed_hash(self):
        """Malformed hash should return False, not raise."""
        assert verify_password("anypassword", "not-a-valid-hash") is False


class TestAccessToken:
    """Tests for JWT access token creation and decoding."""

    def test_create_access_token_basic(self):
        """Create token with default expiration."""
        token = create_access_token({"sub": "user123"})
        assert token
        assert isinstance(token, str)

    def test_create_access_token_custom_expiration(self):
        """Create token with custom expiration delta."""
        token = create_access_token(
            {"sub": "user456"}, expires_delta=timedelta(hours=2)
        )
        assert token
        assert isinstance(token, str)

    def test_decode_token_valid(self):
        """Valid token should decode successfully."""
        user_id = str(uuid4())
        token = create_access_token({"sub": user_id})
        data = decode_token(token)
        assert data.sub == user_id
        assert data.scopes == []

    def test_decode_token_with_scopes(self):
        """Token with scopes should decode correctly."""
        user_id = str(uuid4())
        token = create_access_token({"sub": user_id, "scopes": ["read", "write"]})
        data = decode_token(token)
        assert data.sub == user_id
        assert data.scopes == ["read", "write"]

    def test_decode_token_expired(self):
        """Expired token should raise 401."""
        token = create_access_token(
            {"sub": "user123"}, expires_delta=timedelta(minutes=-1)
        )
        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Could not validate credentials"

    def test_decode_token_invalid(self):
        """Invalid token string should raise 401."""
        with pytest.raises(HTTPException) as exc:
            decode_token("not.a.valid.jwt")
        assert exc.value.status_code == 401

    def test_decode_token_missing_sub(self):
        """Token without sub claim should raise 401."""
        from jose import jwt

        from core.config import get_settings

        settings = get_settings()
        token = jwt.encode(
            {"exp": 9999999999},  # Far future expiration
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Token missing subject"


class TestDraftToken:
    """Tests for draft token creation and decoding."""

    def test_create_draft_token_default_expiration(self):
        """Create draft token with default 1 hour expiration."""
        draft_id = uuid4()
        user_id = uuid4()
        token = create_draft_token(draft_id, user_id)
        assert token
        assert isinstance(token, str)

    def test_create_draft_token_custom_expiration(self):
        """Create draft token with custom expiration."""
        draft_id = uuid4()
        user_id = uuid4()
        token = create_draft_token(draft_id, user_id, exp_delta=timedelta(hours=2))
        assert token
        assert isinstance(token, str)

    def test_decode_draft_token_valid(self):
        """Valid draft token should decode successfully."""
        draft_id = uuid4()
        user_id = uuid4()
        token = create_draft_token(draft_id, user_id)
        payload = decode_draft_token(token)
        assert payload["draft_id"] == str(draft_id)
        assert payload["user_id"] == str(user_id)
        assert payload["type"] == "draft"

    def test_decode_draft_token_expired(self):
        """Expired draft token should raise 401."""
        draft_id = uuid4()
        user_id = uuid4()
        token = create_draft_token(draft_id, user_id, exp_delta=timedelta(minutes=-1))
        with pytest.raises(HTTPException) as exc:
            decode_draft_token(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Invalid or expired draft token"

    def test_decode_draft_token_invalid(self):
        """Invalid draft token should raise 401."""
        with pytest.raises(HTTPException) as exc:
            decode_draft_token("not.a.valid.token")
        assert exc.value.status_code == 401

    def test_decode_draft_token_missing_claims(self):
        """Draft token missing required claims should raise 401."""
        from jose import jwt

        from core.config import get_settings

        settings = get_settings()
        # Token without draft_id, user_id, or type
        token = jwt.encode(
            {"exp": 9999999999},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc:
            decode_draft_token(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Malformed draft token"

    def test_decode_draft_token_wrong_type(self):
        """Draft token with wrong type should raise 401."""
        from jose import jwt

        from core.config import get_settings

        settings = get_settings()
        token = jwt.encode(
            {
                "draft_id": str(uuid4()),
                "user_id": str(uuid4()),
                "type": "wrong",  # Wrong type
                "exp": 9999999999,
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc:
            decode_draft_token(token)
        assert exc.value.status_code == 401
        assert exc.value.detail == "Malformed draft token"


class TestEmailVerificationToken:
    """Tests for email verification token generation and verification."""

    def test_generate_verification_token(self):
        """Generate verification token should return a string."""
        email = "test@example.com"
        token = generate_verification_token(email)
        assert token
        assert isinstance(token, str)

    def test_verify_email_token_valid(self):
        """Valid verification token should return email."""
        email = "test@example.com"
        token = generate_verification_token(email)
        result = verify_email_token(token)
        assert result == email

    def test_verify_email_token_expired(self):
        """Expired verification token should return None."""
        with patch(
            "core.security.URLSafeTimedSerializer.loads",
            side_effect=SignatureExpired("expired"),
        ):
            result = verify_email_token("some-token")
        assert result is None

    def test_verify_email_token_bad_signature(self):
        """Token with bad signature should return None."""
        with patch(
            "core.security.URLSafeTimedSerializer.loads",
            side_effect=BadSignature("bad signature"),
        ):
            result = verify_email_token("some-token")
        assert result is None

    def test_verify_email_token_unexpected_error(self):
        """Unexpected error should return None and log."""
        with patch(
            "core.security.URLSafeTimedSerializer.loads",
            side_effect=ValueError("unexpected"),
        ):
            result = verify_email_token("some-token")
        assert result is None


class TestPasswordResetToken:
    """Tests for password reset token generation and verification."""

    def test_generate_password_reset_token(self):
        """Generate password reset token should return a string."""
        email = "test@example.com"
        token = generate_password_reset_token(email)
        assert token
        assert isinstance(token, str)

    def test_verify_password_reset_token_valid(self):
        """Valid reset token should return email."""
        email = "test@example.com"
        token = generate_password_reset_token(email)
        result = verify_password_reset_token(token)
        assert result == email

    def test_verify_password_reset_token_expired(self):
        """Expired reset token should return None."""
        with patch(
            "core.security.URLSafeTimedSerializer.loads",
            side_effect=SignatureExpired("expired"),
        ):
            result = verify_password_reset_token("some-token")
        assert result is None

    def test_verify_password_reset_token_bad_signature(self):
        """Token with bad signature should return None."""
        with patch(
            "core.security.URLSafeTimedSerializer.loads",
            side_effect=BadSignature("bad signature"),
        ):
            result = verify_password_reset_token("some-token")
        assert result is None

    def test_verify_password_reset_token_unexpected_error(self):
        """Unexpected error should return None and log."""
        with patch(
            "core.security.URLSafeTimedSerializer.loads",
            side_effect=ValueError("unexpected"),
        ):
            result = verify_password_reset_token("some-token")
        assert result is None


class TestTokenConstants:
    """Tests to verify token expiration constants."""

    def test_email_verification_expiration_is_24_hours(self):
        """Email verification token should expire in 24 hours."""
        assert EMAIL_VERIFICATION_EXPIRATION == 86400  # 24 * 60 * 60

    def test_password_reset_expiration_is_1_hour(self):
        """Password reset token should expire in 1 hour."""
        assert PASSWORD_RESET_EXPIRATION == 3600  # 60 * 60
