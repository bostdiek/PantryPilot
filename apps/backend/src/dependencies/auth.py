from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.exc import SQLAlchemyError

from core.security import decode_token
from crud.user import get_user_by_id
from dependencies.db import DbSession
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
