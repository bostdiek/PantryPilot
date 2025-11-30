"""apps/backend/src/api/v1/auth.py: Auth (login) API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from core.exceptions import DuplicateUserError
from core.ratelimit import check_rate_limit
from core.security import create_access_token, get_password_hash, verify_password
from crud.user import create_user, get_user_by_username
from dependencies.db import DbSession
from schemas.auth import Token, UserRegister


router = APIRouter(prefix="/auth", tags=["auth"])

PasswordForm = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/login", response_model=Token, dependencies=[Depends(check_rate_limit)])
async def login(form_data: PasswordForm, db: DbSession) -> Token:
    """
    OAuth2-compatible token login, get an access token for future requests.

    - **username**: The user's username
    - **password**: The user's password
    """
    user = await get_user_by_username(db=db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")


@router.post(
    "/register",
    response_model=Token,
    status_code=201,
    dependencies=[Depends(check_rate_limit)],
)
async def register(payload: UserRegister, db: DbSession) -> Token:
    """
    Register a new user account.

    - **username**: The user's username (3-32 chars, alphanumeric, underscore, hyphen)
    - **email**: Valid email address
    - **password**: Password with minimum length of 12 characters
    - **first_name**: Optional first name
    - **last_name**: Optional last name
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
        # Create user
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

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")
