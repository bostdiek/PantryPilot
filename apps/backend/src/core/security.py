import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import HashingError, VerifyMismatchError
from fastapi import HTTPException, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from jose import JWTError, jwt
from jose.exceptions import JWSSignatureError

from core.config import Settings, get_settings
from schemas.auth import TokenData


def _settings() -> Settings:  # lazy accessor to allow tests to set env first
    return get_settings()


# Reuse a single PasswordHasher instance (Argon2id by default)
_password_hasher = PasswordHasher()

# Module logger for security helpers
_logger = logging.getLogger(__name__)

# Token salts for different purposes
EMAIL_VERIFICATION_SALT = "email-verification"
PASSWORD_RESET_SALT = "password-reset"  # pragma: allowlist secret

# Token expiration times (in seconds)
EMAIL_VERIFICATION_EXPIRATION = 3600  # 1 hour
PASSWORD_RESET_EXPIRATION = 3600  # 1 hour


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


def create_draft_token(
    draft_id: UUID, user_id: UUID, exp_delta: timedelta | None = None
) -> str:
    """Create a signed JWT token for an AI draft.

    Args:
        draft_id: The UUID of the draft
        user_id: The UUID of the user who owns the draft
        exp_delta: Optional expiration delta. If None, defaults to 1 hour.

    Returns:
        Signed JWT token containing draft_id, user_id, and expiration
    """
    if exp_delta is None:
        exp_delta = timedelta(hours=1)

    expire = datetime.now(UTC) + exp_delta
    payload = {
        "draft_id": str(draft_id),
        "user_id": str(user_id),
        "type": "draft",
        "exp": expire,
    }

    s = _settings()
    return jwt.encode(payload, s.SECRET_KEY, algorithm=s.ALGORITHM)


def decode_draft_token(token: str) -> dict[str, Any]:
    """Decode and validate a draft JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        Dict containing draft_id, user_id, and other claims

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    try:
        s = _settings()
        payload = jwt.decode(
            token,
            s.SECRET_KEY,
            algorithms=[s.ALGORITHM],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError as err:
        _logger.warning(
            "Draft token validation failed: expired signature",
            extra={"error_type": "expired"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired draft token",
        ) from err
    except JWSSignatureError as err:
        _logger.warning(
            "Draft token validation failed: invalid signature",
            extra={"error_type": "invalid_signature"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired draft token",
        ) from err
    except JWTError as err:
        _logger.warning(
            "Draft token validation failed: %s",
            type(err).__name__,
            extra={"error_type": "jwt_error"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired draft token",
        ) from err

    # Validate required claims
    draft_id = payload.get("draft_id")
    user_id = payload.get("user_id")
    token_type = payload.get("type")

    if not draft_id or not user_id or token_type != "draft":
        _logger.warning(
            "Draft token validation failed: malformed claims "
            "(draft_id=%s, user_id=%s, type=%s)",
            bool(draft_id),
            bool(user_id),
            token_type,
            extra={"error_type": "malformed"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed draft token",
        )

    return payload


def _get_serializer() -> URLSafeTimedSerializer:
    """Get a URLSafeTimedSerializer instance using the app secret key."""
    return URLSafeTimedSerializer(_settings().SECRET_KEY)


def generate_verification_token(email: str) -> str:
    """Generate a URL-safe token for email verification.

    Args:
        email: The email address to encode in the token.

    Returns:
        A URL-safe token string.
    """
    serializer = _get_serializer()
    return serializer.dumps(email, salt=EMAIL_VERIFICATION_SALT)


def verify_email_token(token: str) -> str | None:
    """Verify an email verification token and extract the email.

    Args:
        token: The token to verify.

    Returns:
        The email address if the token is valid, None otherwise.
    """
    serializer = _get_serializer()
    try:
        email: str = serializer.loads(
            token,
            salt=EMAIL_VERIFICATION_SALT,
            max_age=EMAIL_VERIFICATION_EXPIRATION,
        )
        return email
    except SignatureExpired:
        _logger.warning("Email verification token expired")
        return None
    except BadSignature:
        _logger.warning("Invalid email verification token signature")
        return None
    except Exception as exc:
        _logger.exception("Unexpected error verifying email token: %s", exc)
        return None


def generate_password_reset_token(email: str) -> str:
    """Generate a URL-safe token for password reset.

    Args:
        email: The email address to encode in the token.

    Returns:
        A URL-safe token string.
    """
    serializer = _get_serializer()
    return serializer.dumps(email, salt=PASSWORD_RESET_SALT)


def verify_password_reset_token(token: str) -> str | None:
    """Verify a password reset token and extract the email.

    Args:
        token: The token to verify.

    Returns:
        The email address if the token is valid, None otherwise.
    """
    serializer = _get_serializer()
    try:
        email: str = serializer.loads(
            token,
            salt=PASSWORD_RESET_SALT,
            max_age=PASSWORD_RESET_EXPIRATION,
        )
        return email
    except SignatureExpired:
        _logger.warning("Password reset token expired")
        return None
    except BadSignature:
        _logger.warning("Invalid password reset token signature")
        return None
    except Exception as exc:
        _logger.exception("Unexpected error verifying password reset token: %s", exc)
        return None
