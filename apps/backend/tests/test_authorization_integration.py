"""Integration tests for authorization at the endpoint level."""

from __future__ import annotations

import uuid

import pytest
from fastapi import status
from httpx import AsyncClient

from dependencies.auth import check_resource_access, check_resource_write_access
from models.recipes_names import Recipe
from models.users import User


class MockRecipeForAuth:
    """Mock recipe object for testing authorization at endpoint level."""

    def __init__(self, user_id: uuid.UUID | None, recipe_id: uuid.UUID | None = None):
        self.user_id = user_id
        self.id = recipe_id or uuid.uuid4()


class TestEndpointAuthorization:
    """Test authorization behavior at the API endpoint level."""

    def test_recipe_authorization_user_can_access_own_recipe(self):
        """Test that a user can access their own recipe through authorization check."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            username="user",
            email="user@test.com",
            hashed_password="hash",
            is_admin=False,
        )
        recipe = MockRecipeForAuth(user_id=user_id)

        result = check_resource_access(recipe, user)
        assert result == recipe

    def test_recipe_authorization_admin_can_access_any_recipe(self):
        """Test that admin users can access any recipe through authorization check."""
        admin_id = uuid.uuid4()
        admin_user = User(
            id=admin_id,
            username="admin",
            email="admin@test.com",
            hashed_password="hash",
            is_admin=True,
        )

        other_user_id = uuid.uuid4()
        recipe = MockRecipeForAuth(user_id=other_user_id)

        result = check_resource_access(recipe, admin_user)
        assert result == recipe

    def test_recipe_authorization_non_owner_cannot_access(self):
        """Test that non-owners cannot access recipes through authorization check."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            username="user",
            email="user@test.com",
            hashed_password="hash",
            is_admin=False,
        )

        other_user_id = uuid.uuid4()
        recipe = MockRecipeForAuth(user_id=other_user_id)

        with pytest.raises(Exception) as exc_info:
            check_resource_access(recipe, user)

        # Should return 404 to avoid leaking resource existence
        assert hasattr(exc_info.value, 'status_code')
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_recipe_write_authorization_user_can_modify_own_recipe(self):
        """Test that a user can modify their own recipe through write authorization check."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            username="user",
            email="user@test.com",
            hashed_password="hash",
            is_admin=False,
        )
        recipe = MockRecipeForAuth(user_id=user_id)

        result = check_resource_write_access(recipe, user)
        assert result == recipe

    def test_legacy_recipe_authorization_allows_access(self):
        """Test that legacy recipes with null user_id are accessible."""
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            username="user",
            email="user@test.com",
            hashed_password="hash",
            is_admin=False,
        )

        # Create a legacy recipe without user_id
        legacy_recipe = MockRecipeForAuth(user_id=None)

        result = check_resource_access(legacy_recipe, user)
        assert result == legacy_recipe

    def test_admin_override_can_be_disabled(self):
        """Test that admin override can be disabled for specific resources."""
        admin_id = uuid.uuid4()
        admin_user = User(
            id=admin_id,
            username="admin",
            email="admin@test.com",
            hashed_password="hash",
            is_admin=True,
        )

        other_user_id = uuid.uuid4()
        recipe = MockRecipeForAuth(user_id=other_user_id)

        with pytest.raises(Exception) as exc_info:
            check_resource_access(recipe, admin_user, allow_admin_override=False)

        assert hasattr(exc_info.value, 'status_code')
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# Note: Full endpoint integration tests would require database setup and 
# HTTP client testing. These tests focus on the authorization logic patterns
# that would be used by the actual endpoints.