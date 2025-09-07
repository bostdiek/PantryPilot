
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token
from crud.user import create_user, get_user_by_username
from models.users import User


async def _create_test_user(db: AsyncSession, username: str = "testuser") -> User:
    """Create a test user."""
    from core.security import get_password_hash
    
    existing = await get_user_by_username(db, username)
    if existing:
        return existing
    
    return await create_user(
        db,
        email=f"{username}@example.com", 
        username=username,
        hashed_password=get_password_hash("password123"),
        first_name="Test",
        last_name="User"
    )


class TestUserPreferencesAPI:
    """Test user preferences API endpoints."""

    @pytest.mark.skip(
        reason="PostgreSQL ARRAY types not compatible with SQLite test environment"
    )
    @pytest.mark.asyncio
    async def test_get_user_profile_creates_default_preferences(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Test that getting user profile creates default preferences if none exist."""
        pass

    @pytest.mark.skip(
        reason="PostgreSQL ARRAY types not compatible with SQLite test environment"
    )
    @pytest.mark.asyncio
    async def test_update_user_preferences(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Test updating user preferences."""
        pass

    @pytest.mark.skip(
        reason="PostgreSQL ARRAY types not compatible with SQLite test environment"
    )
    @pytest.mark.asyncio
    async def test_update_user_profile_info(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Test updating user profile information."""
        pass

    @pytest.mark.asyncio
    async def test_preferences_validation(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Test preferences validation."""
        client, db = auth_client
        user = await _create_test_user(db, "validuser")
        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test invalid family size
        update_data = {"family_size": 0}  # Invalid - must be >= 1
        
        response = await client.patch(
            "/api/v1/users/me/preferences", 
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid theme
        update_data = {"theme": "invalid_theme"}
        
        response = await client.patch(
            "/api/v1/users/me/preferences", 
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY