from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Protocol, TypeVar, cast
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from core.security import decode_token
from core.session import session_has_expired
from crud.user import get_user_by_id
from dependencies.db import DbSession
from models.auth_sessions import AuthSession
from models.users import User


# --------------------------------------------------------------------------- #
# Common constants / helpers
# --------------------------------------------------------------------------- #
LOGGER = logging.getLogger(__name__)
BEARER = "Bearer"


def unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    """Return the canonical 401 response."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": BEARER},
    )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# --------------------------------------------------------------------------- #
# The dependency
# --------------------------------------------------------------------------- #
async def get_current_user(
    db: DbSession,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    """
    Resolve the currently authenticated user from a JWT.

    Raises
    ------
    HTTPException(401)
        If the token is missing, malformed, expired, or the user does not exist.
    """

    # Decode the JWT – `decode_token` raises HTTPException(401) on failure,
    # so allow that to surface instead of catching a broad Exception here.
    token_data = decode_token(token)

    session_id = token_data.sid
    if session_id:
        try:
            session_uuid = UUID(session_id)
        except ValueError as exc:
            raise unauthorized() from exc

        auth_session = await db.scalar(
            select(AuthSession).where(AuthSession.id == session_uuid)
        )
        now = datetime.now(UTC)
        if auth_session is None or auth_session.revoked_at is not None:
            raise unauthorized("Session expired. Please sign in again.")

        if session_has_expired(
            auth_session.created_at, auth_session.last_activity_at, now
        ):
            auth_session.revoked_at = now
            await db.commit()
            raise unauthorized(
                "Your session ended due to inactivity or its maximum duration. "
                "Please sign in again."
            )

    # Validate the subject claim
    sub = getattr(token_data, "sub", None)
    if not sub:
        LOGGER.debug("Token missing 'sub' claim")
        raise unauthorized()

    # Convert `sub` to a UUID
    try:
        user_id = UUID(sub)
    except ValueError as exc:
        LOGGER.debug("Token 'sub' is not a valid UUID", exc_info=exc)
        raise unauthorized() from exc

    # Pull the user from the DB
    try:
        user = await get_user_by_id(db, user_id)
    except SQLAlchemyError as exc:  # pragma: no cover - DB errors should be explicit
        LOGGER.error("DB lookup failed", exc_info=exc)
        # Let FastAPI surface a 500 – or raise a custom 503 if you prefer
        raise

    if user is None:
        LOGGER.debug("User not found for sub=%s", sub)
        raise unauthorized()

    return user


# --------------------------------------------------------------------------- #
# Authorization helpers
# --------------------------------------------------------------------------- #


class HasUserIdProtocol(Protocol):
    """Protocol for database models that have a user_id field."""

    user_id: UUID | None


ResourceT = TypeVar("ResourceT", bound=HasUserIdProtocol)


def forbidden(detail: str = "Access denied") -> HTTPException:
    """Return the canonical 403 response."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail,
    )


def not_found(detail: str = "Resource not found") -> HTTPException:
    """Return the canonical 404 response."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )


def check_resource_access[ResourceT](
    resource: ResourceT | None,
    current_user: User,
    *,
    allow_admin_override: bool = True,
    not_found_message: str = "Resource not found",
    forbidden_message: str = "Access denied",
) -> ResourceT:
    """Check if current user can access a resource based on ownership or admin status.

    Args:
        resource: The resource to check, or None if not found
        current_user: The authenticated user
        allow_admin_override: Whether admin users can access any resource
        not_found_message: Message for 404 errors
        forbidden_message: Message for 403 errors

    Returns:
        The resource if access is allowed

    Raises:
        HTTPException: 404 if resource not found, 403 if access denied
    """
    # Resource not found
    if resource is None:
        raise not_found(not_found_message)

    # Narrow to the protocol so type checkers without full PEP-695 support
    # know the resource has a `user_id` attribute.
    resource_h = cast(HasUserIdProtocol, resource)

    # Ownerless resources are never accessible, including during rollback.
    if resource_h.user_id is None:
        LOGGER.warning("Denied access to resource without user_id")
        raise not_found(not_found_message)

    # Admin override
    if allow_admin_override and current_user.is_admin:
        return resource

    # Owner check
    if resource_h.user_id == current_user.id:
        return resource

    # Access denied - return 404 to avoid leaking resource existence
    raise not_found(not_found_message)


def check_resource_write_access[ResourceT](
    resource: ResourceT | None,
    current_user: User,
    *,
    allow_admin_override: bool = True,
    not_found_message: str = "Resource not found",
    forbidden_message: str = "Not allowed to modify this resource",
) -> ResourceT:
    """Check if current user can modify a resource.

    This is similar to check_resource_access but may have different
    permission rules in the future (e.g., read-only sharing).
    """
    return check_resource_access(
        resource,
        current_user,
        allow_admin_override=allow_admin_override,
        not_found_message=not_found_message,
        forbidden_message=forbidden_message,
    )
