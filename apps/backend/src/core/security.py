from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from fastapi import HTTPException, status
from jose import JWTError, jwt

from core.config import get_settings
from schemas.auth import TokenData


settings = get_settings()

# Reuse a single PasswordHasher instance (Argon2id by default)
_password_hasher = PasswordHasher()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Encodes a JWT with `sub` (subject) and expiry"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an Argon2 hash.

    Do NOT hash the plaintext and compare strings — Argon2 uses a random salt,
    so re-hashing the same password yields a different hash. Always use verify().
    """
    try:
        return _password_hasher.verify(hashed, plain)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _password_hasher.hash(password)


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT, returning TokenData or raising 401.

    Expects a `sub` claim (user identifier). Also supports optional `scopes`.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
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
