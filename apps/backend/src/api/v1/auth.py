"""apps/backend/src/api/v1/auth.py: Auth (login) API routes."""

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from core.config import get_settings
from core.email import send_password_reset_email, send_verification_email
from core.exceptions import DuplicateUserError
from core.ratelimit import check_rate_limit
from core.session import SESSION_ABSOLUTE_TIMEOUT, session_has_expired
from core.security import (
    create_access_token,
    generate_password_reset_token,
    generate_verification_token,
    get_password_hash,
    verify_email_token,
    verify_password,
    verify_password_reset_token,
)
from crud.user import create_user, get_user_by_email, get_user_by_username, user_crud
from dependencies.db import DbSession
from models.auth_sessions import AuthSession
from schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    RegisterResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SessionActivity,
    Token,
    UserRegister,
    VerifyEmailRequest,
    VerifyEmailResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])

PasswordForm = Annotated[OAuth2PasswordRequestForm, Depends()]

_logger = logging.getLogger(__name__)
REFRESH_COOKIE = "pantrypilot_session"
SESSION_ABSOLUTE_SECONDS = int(SESSION_ABSOLUTE_TIMEOUT.total_seconds())


def _refresh_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _refresh_secret(session_id: UUID, generation: int) -> str:
    key = get_settings().SECRET_KEY.encode("utf-8")
    message = f"pantrypilot-refresh:{session_id}:{generation}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _set_refresh_cookie(response: Response, token: str, max_age: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE,
        # The browser-only credential is protected by HttpOnly/SameSite and
        # the Secure flag in production.
        value=token,  # codeql[py/clear-text-storage-sensitive-data]
        max_age=max_age,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        path="/api/v1/auth",
    )


async def _create_session(user_id: UUID, db: DbSession, response: Response) -> str:
    session_id = UUID(bytes=secrets.token_bytes(16), version=4)
    refresh_secret = _refresh_secret(session_id, 0)
    refresh_token = f"{session_id}.0.{refresh_secret}"
    now = datetime.now(UTC)
    db.add(
        AuthSession(
            id=session_id,
            user_id=user_id,
            refresh_token_hash=_refresh_token_hash(refresh_secret),
            refresh_generation=0,
            created_at=now,
            last_activity_at=now,
        )
    )
    await db.commit()
    _set_refresh_cookie(response, refresh_token, SESSION_ABSOLUTE_SECONDS)
    response.headers["Cache-Control"] = "no-store"
    return create_access_token({"sub": str(user_id), "sid": str(session_id)})


def _delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        httponly=True,
        secure=get_settings().ENVIRONMENT == "production",
        samesite="lax",
        path="/api/v1/auth",
    )


def _invalid_refresh(response: Response, detail: str) -> HTTPException:
    _delete_refresh_cookie(response)
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"Set-Cookie": response.headers["set-cookie"]},
    )


@router.post("/login", response_model=Token, dependencies=[Depends(check_rate_limit)])
async def login(form_data: PasswordForm, db: DbSession, response: Response) -> Token:
    """
    OAuth2-compatible token login, get an access token for future requests.

    - **username**: The user's username or email address
    - **password**: The user's password

    Note: Users must verify their email before logging in.
    """
    # Try to find user by username first, then by email
    user = await get_user_by_username(db=db, username=form_data.username)
    if not user:
        # If not found by username, try email (case-insensitive)
        user = await get_user_by_email(db=db, email=form_data.username.lower())

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user has verified their email
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox for the "
            "verification link.",
        )

    access_token = await _create_session(user.id, db, response)
    return Token(access_token=access_token, token_type="bearer")


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
    dependencies=[Depends(check_rate_limit)],
)
async def register(payload: UserRegister, db: DbSession) -> RegisterResponse:
    """
    Register a new user account.

    - **username**: The user's username (3-32 chars, alphanumeric, underscore, hyphen)
    - **email**: Valid email address
    - **password**: Password with minimum length of 12 characters
    - **first_name**: Optional first name
    - **last_name**: Optional last name

    After registration, a verification email will be sent to the provided address.
    Users must verify their email before logging in.
    """
    # Normalize email to lowercase
    email = payload.email.lower()

    # Validate password length (≥ 12 characters)
    if len(payload.password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password too short",
        )

    # Hash the password
    hashed_password = get_password_hash(payload.password)

    try:
        # Create user (is_verified defaults to False)
        user = await create_user(
            db=db,
            email=email,
            username=payload.username,
            hashed_password=hashed_password,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
    except DuplicateUserError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        ) from err

    # Generate verification token and send email
    verification_token = generate_verification_token(email)
    email_sent = send_verification_email(email, verification_token)

    if not email_sent:
        _logger.warning(
            "Failed to send verification email to %s (user_id=%s). "
            "Email service may be unavailable.",
            email,
            user.id,
        )

    return RegisterResponse(
        message="Registration successful. Please check your email to verify "
        "your account.",
        email=email,
    )


@router.post(
    "/verify-email",
    response_model=VerifyEmailResponse,
    dependencies=[Depends(check_rate_limit)],
)
async def verify_email(
    payload: VerifyEmailRequest, db: DbSession, response: Response
) -> VerifyEmailResponse:
    """
    Verify a user's email address using the token from the verification link.

    - **token**: The verification token from the email link

    Upon successful verification, returns an access token for immediate login.
    """
    # Verify the token and extract email
    email = verify_email_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Find the user by email
    user = await get_user_by_email(db=db, email=email.lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if already verified
    if user.is_verified:
        # Still return a token for convenience
        access_token = await _create_session(user.id, db, response)
        return VerifyEmailResponse(
            message="Email already verified",
            access_token=access_token,
            token_type="bearer",
        )

    # Mark user as verified
    await user_crud.set_verified(db=db, user=user)

    # Create access token for immediate login
    access_token = await _create_session(user.id, db, response)

    return VerifyEmailResponse(
        message="Email verified successfully",
        access_token=access_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh_session(
    payload: SessionActivity,
    db: DbSession,
    response: Response,
    request: Request,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Token:
    """Issue a short-lived access token for an active server-side session."""
    origin = request.headers.get("origin")
    if origin and origin not in get_settings().CORS_ORIGINS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid origin"
        )
    if not refresh_token:
        raise _invalid_refresh(response, "Your session ended. Please sign in again.")

    try:
        session_id_text, generation_text, refresh_secret = refresh_token.split(
            ".", maxsplit=2
        )
        session_id = UUID(session_id_text)
        presented_generation = int(generation_text)
    except ValueError as exc:
        raise _invalid_refresh(
            response, "Your session ended. Please sign in again."
        ) from exc

    auth_session = await db.scalar(
        select(AuthSession)
        .where(AuthSession.id == session_id)
        .with_for_update()
    )
    if auth_session is None:
        raise _invalid_refresh(response, "Your session ended. Please sign in again.")

    now = datetime.now(UTC)
    if auth_session.revoked_at is not None or session_has_expired(
        auth_session.created_at, auth_session.last_activity_at, now
    ):
        auth_session.revoked_at = auth_session.revoked_at or now
        await db.commit()
        raise _invalid_refresh(
            response,
            "Your session ended due to inactivity or its maximum duration. "
            "Please sign in again.",
        )

    presented_hash = _refresh_token_hash(refresh_secret)
    secret_is_valid = secrets.compare_digest(
        _refresh_secret(auth_session.id, presented_generation), refresh_secret
    )
    is_current_token = (
        presented_generation == auth_session.refresh_generation
        and secrets.compare_digest(auth_session.refresh_token_hash, presented_hash)
        and secret_is_valid
    )
    grace_started_at = auth_session.refresh_grace_started_at
    if grace_started_at is not None and grace_started_at.tzinfo is None:
        grace_started_at = grace_started_at.replace(tzinfo=UTC)
    is_recent_previous_token = (
        auth_session.refresh_grace_generation is not None
        and auth_session.refresh_grace_generation
        <= presented_generation
        < auth_session.refresh_generation
        and secret_is_valid
        and grace_started_at is not None
        and now - grace_started_at <= timedelta(seconds=30)
    )
    if not is_current_token and not is_recent_previous_token:
        if secret_is_valid and presented_generation < auth_session.refresh_generation:
            auth_session.revoked_at = now
            await db.commit()
        raise _invalid_refresh(response, "Your session ended. Please sign in again.")

    if is_current_token:
        if (
            grace_started_at is None
            or now - grace_started_at > timedelta(seconds=30)
        ):
            auth_session.refresh_grace_started_at = now
            auth_session.refresh_grace_generation = auth_session.refresh_generation
        auth_session.refresh_generation += 1
        new_secret = _refresh_secret(
            auth_session.id, auth_session.refresh_generation
        )
        auth_session.refresh_token_hash = _refresh_token_hash(new_secret)

    if payload.activity:
        auth_session.last_activity_at = now
    if is_current_token or payload.activity:
        await db.commit()

    current_secret = _refresh_secret(
        auth_session.id, auth_session.refresh_generation
    )
    remaining_seconds = max(
        0,
        SESSION_ABSOLUTE_SECONDS
        - int(
            (
                now
                - (
                    auth_session.created_at.replace(tzinfo=UTC)
                    if auth_session.created_at.tzinfo is None
                    else auth_session.created_at
                )
            ).total_seconds()
        ),
    )
    _set_refresh_cookie(
        response,
        f"{auth_session.id}.{auth_session.refresh_generation}.{current_secret}",
        remaining_seconds,
    )

    response.headers["Cache-Control"] = "no-store"
    access_token = create_access_token(
        {"sub": str(auth_session.user_id), "sid": str(auth_session.id)}
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_session(
    db: DbSession,
    response: Response,
    request: Request,
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    """Revoke this browser session and clear its refresh credential."""
    origin = request.headers.get("origin")
    if origin and origin not in get_settings().CORS_ORIGINS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid origin"
        )

    if refresh_token:
        try:
            session_id_text, generation_text, refresh_secret = refresh_token.split(
                ".", maxsplit=2
            )
            session_id = UUID(session_id_text)
            presented_generation = int(generation_text)
        except ValueError:
            session_id = None
            refresh_secret = ""
            presented_generation = -1

        if session_id:
            auth_session = await db.scalar(
                select(AuthSession)
                .where(AuthSession.id == session_id)
                .with_for_update()
            )
            if auth_session:
                presented_hash = _refresh_token_hash(refresh_secret)
                if (
                    0 <= presented_generation <= auth_session.refresh_generation
                    and secrets.compare_digest(
                        _refresh_secret(auth_session.id, presented_generation),
                        refresh_secret,
                    )
                    and (
                        presented_generation != auth_session.refresh_generation
                        or secrets.compare_digest(
                            auth_session.refresh_token_hash, presented_hash
                        )
                    )
                ):
                    auth_session.revoked_at = datetime.now(UTC)
                    await db.commit()

    _delete_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    dependencies=[Depends(check_rate_limit)],
)
async def forgot_password(
    payload: ForgotPasswordRequest, db: DbSession
) -> ForgotPasswordResponse:
    """
    Request a password reset email.

    - **email**: The email address associated with the account

    For security, this endpoint always returns success even if the email
    is not registered.
    """
    email = payload.email.lower()

    # Look up user by email
    user = await get_user_by_email(db=db, email=email)

    if user:
        # Generate reset token and send email
        reset_token = generate_password_reset_token(email)
        email_sent = send_password_reset_email(email, reset_token)

        if not email_sent:
            _logger.warning(
                "Failed to send password reset email to %s (user_id=%s). "
                "Email service may be unavailable.",
                email,
                user.id,
            )
    else:
        # Don't reveal that email doesn't exist
        _logger.info("Password reset requested for non-existent email: %s", email)

    # Always return success to prevent email enumeration
    return ForgotPasswordResponse(
        message="If an account with that email exists, "
        "a password reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    dependencies=[Depends(check_rate_limit)],
)
async def reset_password(
    payload: ResetPasswordRequest, db: DbSession
) -> ResetPasswordResponse:
    """
    Reset a user's password using the token from the reset email.

    - **token**: The password reset token from the email link
    - **new_password**: The new password (minimum 12 characters)
    """
    # Verify the token and extract email
    email = verify_password_reset_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Find the user by email
    user = await get_user_by_email(db=db, email=email.lower())
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Validate new password length
    if len(payload.new_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters",
        )

    # Hash and update the password
    hashed_password = get_password_hash(payload.new_password)
    await user_crud.update_password(db=db, user=user, hashed_password=hashed_password)

    return ResetPasswordResponse(message="Password reset successfully")


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    dependencies=[Depends(check_rate_limit)],
)
async def resend_verification(
    payload: ResendVerificationRequest, db: DbSession
) -> ResendVerificationResponse:
    """
    Resend the verification email to a user.

    - **email**: The email address to resend verification to

    For security, this endpoint always returns success even if the email
    is not registered or already verified. Rate limited to prevent abuse.
    """
    email = payload.email.lower()
    user = await get_user_by_email(db=db, email=email)

    if user and not user.is_verified:
        verification_token = generate_verification_token(email)
        email_sent = send_verification_email(email, verification_token)
        if not email_sent:
            _logger.warning("Failed to resend verification email to %s", email)
    else:
        _logger.info(
            "Resend verification requested for %s (not found or already verified)",
            email,
        )

    # Always return success to prevent email enumeration
    return ResendVerificationResponse(
        message="If an unverified account exists with that email, "
        "a new verification link has been sent."
    )
