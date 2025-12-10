"""apps/backend/src/api/v1/auth.py: Auth (login) API routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from core.email import send_password_reset_email, send_verification_email
from core.exceptions import DuplicateUserError
from core.ratelimit import check_rate_limit
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
from schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    RegisterResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    Token,
    UserRegister,
    VerifyEmailRequest,
    VerifyEmailResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])

PasswordForm = Annotated[OAuth2PasswordRequestForm, Depends()]

_logger = logging.getLogger(__name__)


@router.post("/login", response_model=Token, dependencies=[Depends(check_rate_limit)])
async def login(form_data: PasswordForm, db: DbSession) -> Token:
    """
    OAuth2-compatible token login, get an access token for future requests.

    - **username**: The user's username
    - **password**: The user's password

    Note: Users must verify their email before logging in.
    """
    user = await get_user_by_username(db=db, username=form_data.username)
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

    access_token = create_access_token(data={"sub": str(user.id)})
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


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    payload: VerifyEmailRequest, db: DbSession
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
        access_token = create_access_token(data={"sub": str(user.id)})
        return VerifyEmailResponse(
            message="Email already verified",
            access_token=access_token,
            token_type="bearer",
        )

    # Mark user as verified
    await user_crud.set_verified(db=db, user=user)

    # Create access token for immediate login
    access_token = create_access_token(data={"sub": str(user.id)})

    return VerifyEmailResponse(
        message="Email verified successfully",
        access_token=access_token,
        token_type="bearer",
    )


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


@router.post("/reset-password", response_model=ResetPasswordResponse)
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
