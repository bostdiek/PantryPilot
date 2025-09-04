"""apps/backend/src/api/v1/auth.py: Auth (login) API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from core.security import create_access_token, verify_password
from crud.user import get_user_by_username
from dependencies.db import DbSession
from schemas.auth import Token


router = APIRouter(prefix="", tags=["auth"])

PasswordForm = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/login", response_model=Token)
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
