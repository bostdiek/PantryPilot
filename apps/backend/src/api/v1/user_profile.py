from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import GeocodingFailedError
from crud.user import user_crud
from crud.user_preferences import user_preferences_crud
from dependencies.auth import get_current_user
from dependencies.db import get_db
from models.users import User
from schemas.user_preferences import (
    UserPreferencesCreate,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfileResponse:
    """Get current user's profile with preferences."""
    # Get user preferences (create if they don't exist)
    preferences = await user_preferences_crud.get_or_create(db, current_user.id)

    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        preferences=UserPreferencesResponse.model_validate(preferences),
    )


@router.patch("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    profile_update: UserProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfileResponse:
    """Update current user's profile information."""
    # Check if username is already taken (if being updated)
    if profile_update.username and profile_update.username != current_user.username:
        existing_user = await user_crud.get_by_username(db, profile_update.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

    # Update user profile
    updated_user = await user_crud.update(db, current_user, profile_update)

    # Get user preferences
    preferences = await user_preferences_crud.get_or_create(db, updated_user.id)

    return UserProfileResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        preferences=UserPreferencesResponse.model_validate(preferences),
    )


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_current_user_preferences(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferencesResponse:
    """Get current user's preferences."""
    preferences = await user_preferences_crud.get_or_create(db, current_user.id)
    return UserPreferencesResponse.model_validate(preferences)


@router.patch("/me/preferences", response_model=UserPreferencesResponse)
async def update_current_user_preferences(
    preferences_update: UserPreferencesUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferencesResponse:
    """Update current user's preferences."""
    # Get existing preferences (create if they don't exist)
    preferences = await user_preferences_crud.get_or_create(db, current_user.id)

    # Update preferences
    try:
        updated_preferences = await user_preferences_crud.update(
            db, preferences, preferences_update
        )
    except GeocodingFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return UserPreferencesResponse.model_validate(updated_preferences)


@router.post("/me/preferences", response_model=UserPreferencesResponse)
async def create_current_user_preferences(
    preferences_create: UserPreferencesCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserPreferencesResponse:
    """Create or replace current user's preferences."""
    # Check if preferences already exist
    existing_preferences = await user_preferences_crud.get_by_user_id(
        db, current_user.id
    )

    if existing_preferences:
        # Update existing preferences with new data
        update_data = UserPreferencesUpdate(**preferences_create.model_dump())
        try:
            updated_preferences = await user_preferences_crud.update(
                db, existing_preferences, update_data
            )
        except GeocodingFailedError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        return UserPreferencesResponse.model_validate(updated_preferences)
    else:
        # Create new preferences
        new_preferences = await user_preferences_crud.create(
            db, current_user.id, preferences_create
        )
        return UserPreferencesResponse.model_validate(new_preferences)
