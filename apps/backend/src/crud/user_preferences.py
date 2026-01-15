from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_preferences import UserPreferences
from schemas.user_preferences import UserPreferencesCreate, UserPreferencesUpdate
from services.geocoding import GeocodingService


class UserPreferencesCRUD:
    """CRUD operations for user preferences."""

    async def get_by_user_id(
        self, db: AsyncSession, user_id: UUID
    ) -> UserPreferences | None:
        """Get user preferences by user ID."""
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self, db: AsyncSession, user_id: UUID, preferences_data: UserPreferencesCreate
    ) -> UserPreferences:
        """Create new user preferences."""
        preferences = UserPreferences(
            user_id=user_id, **preferences_data.model_dump(exclude_unset=True)
        )
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)
        return preferences

    async def update(
        self,
        db: AsyncSession,
        db_preferences: UserPreferences,
        preferences_update: UserPreferencesUpdate,
    ) -> UserPreferences:
        """Update existing user preferences.

        If location fields change, triggers geocoding to update lat/lon/timezone.
        """
        update_data = preferences_update.model_dump(exclude_unset=True)

        # Check if location fields are being updated
        location_fields = {"city", "state_or_region", "postal_code", "country"}
        location_changed = bool(location_fields & update_data.keys())

        # Apply updates
        for field, value in update_data.items():
            setattr(db_preferences, field, value)

        # Trigger geocoding if location changed
        if location_changed:
            geocoding_service = GeocodingService(db)
            await geocoding_service.update_geocoded_fields(db_preferences)
        else:
            await db.commit()
            await db.refresh(db_preferences)

        return db_preferences

    async def get_or_create(
        self,
        db: AsyncSession,
        user_id: UUID,
        preferences_data: UserPreferencesCreate | None = None,
    ) -> UserPreferences:
        """Get existing preferences or create with defaults."""
        preferences = await self.get_by_user_id(db, user_id)
        if preferences is None:
            # Create with provided data or defaults
            create_data = preferences_data or UserPreferencesCreate()
            preferences = await self.create(db, user_id, create_data)
        return preferences

    async def delete(self, db: AsyncSession, user_id: UUID) -> bool:
        """Delete user preferences by user ID."""
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        preferences = result.scalar_one_or_none()
        if preferences:
            await db.delete(preferences)
            await db.commit()
            return True
        return False


# Create singleton instance
user_preferences_crud = UserPreferencesCRUD()
