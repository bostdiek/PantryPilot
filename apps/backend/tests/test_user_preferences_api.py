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

    @pytest.mark.asyncio
    async def test_get_user_profile_creates_default_preferences(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Test that getting user profile creates default preferences if none exist."""
        client, db = auth_client
        user = await _create_test_user(db)
        
        # Create token for auth
        token = create_access_token({"sub": str(user.id)})
        
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == str(user.id)
        assert data["username"] == user.username
        assert data["email"] == user.email
        assert data["preferences"] is not None
        
        # Check default preferences values
        prefs = data["preferences"]
        assert prefs["family_size"] == 2
        assert prefs["default_servings"] == 4
        assert prefs["allergies"] == []
        assert prefs["dietary_restrictions"] == []
        assert prefs["theme"] == "light"
        assert prefs["units"] == "imperial"
        assert prefs["meal_planning_days"] == 7
        assert prefs["preferred_cuisines"] == []

    @pytest.mark.asyncio
    async def test_update_user_preferences(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Test updating user preferences."""
        client, db = auth_client
        user = await _create_test_user(db, "prefuser")
        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        
        # First create preferences by getting profile
        await client.get("/api/v1/users/me", headers=headers)
        
        # Update preferences
        update_data = {
            "family_size": 4,
            "default_servings": 6,
            "allergies": ["Peanuts", "Shellfish"],
            "dietary_restrictions": ["Vegetarian"],
            "theme": "dark",
            "units": "metric",
            "meal_planning_days": 14,
            "preferred_cuisines": ["Italian", "Mexican"]
        }
        
        response = await client.patch(
            "/api/v1/users/me/preferences", 
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["family_size"] == 4
        assert data["default_servings"] == 6
        assert data["allergies"] == ["Peanuts", "Shellfish"]
        assert data["dietary_restrictions"] == ["Vegetarian"]
        assert data["theme"] == "dark"
        assert data["units"] == "metric"
        assert data["meal_planning_days"] == 14
        assert data["preferred_cuisines"] == ["Italian", "Mexican"]

    @pytest.mark.asyncio
    async def test_update_user_profile_info(
        self, auth_client: tuple[AsyncClient, AsyncSession]
    ):
        """Test updating user profile information."""
        client, db = auth_client
        user = await _create_test_user(db, "profileuser")
        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}
        
        update_data = {
            "first_name": "John",
            "last_name": "Doe",
        }
        
        response = await client.patch(
            "/api/v1/users/me", 
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["username"] == user.username
        assert data["preferences"] is not None

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