import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import HashingError, VerifyMismatchError
from fastapi import HTTPException, status
from jose import JWTError, jwt

from core.config import Settings, get_settings
from schemas.auth import TokenData


def _settings() -> Settings:  # lazy accessor to allow tests to set env first
    return get_settings()


# Reuse a single PasswordHasher instance (Argon2id by default)
_password_hasher = PasswordHasher()

# Module logger for security helpers
_logger = logging.getLogger(__name__)


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Encodes a JWT with `sub` (subject) and expiry"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=_settings().ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    s = _settings()
    encoded_jwt = jwt.encode(to_encode, s.SECRET_KEY, algorithm=s.ALGORITHM)
    return encoded_jwt


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2 hash.

    Uses Argon2's verify which handles salts internally. Returns False for
    verification failures. Unexpected errors are logged and result in False to
    avoid leaking exception traces to callers.
    """
    try:
        return _password_hasher.verify(hashed, plain)
    except (VerifyMismatchError, HashingError):
        # Expected verification / hashing failures
        return False
    except Exception as exc:  # pragma: no cover - defensive logging path
        # Log unexpected errors for operational visibility, but don't raise
        # to keep caller semantics simple.
        _logger.exception("Unexpected error verifying password: %s", exc)
        return False


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _password_hasher.hash(password)


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT, returning TokenData or raising 401.

    Expects a `sub` claim (user identifier). Also supports optional `scopes`.
    """
    try:
        s = _settings()
        payload = jwt.decode(
            token,
            s.SECRET_KEY,
            algorithms=[s.ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    sub = payload.get("sub")
    scopes = payload.get("scopes", [])
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenData(
        sub=str(sub),
        scopes=list(scopes) if isinstance(scopes, list) else [],
    )
