"""Simple tests for authorization functions without complex database setup."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException, status

from dependencies.auth import check_resource_access, check_resource_write_access
from models.users import User


class MockResource:
    """Mock resource object for testing authorization."""
    
    def __init__(self, user_id: uuid.UUID | None):
        self.user_id = user_id


class TestAuthorizationHelpers:
    """Test the authorization helper functions directly."""
    
    def test_check_resource_access_with_owner(self):
        """Test that resource owners can access their resources."""
        user_id = uuid.uuid4()
        user = User(id=user_id, username="user", email="user@test.com", hashed_password="hash", is_admin=False)
        resource = MockResource(user_id=user_id)
        
        result = check_resource_access(resource, user)
        assert result == resource

    def test_check_resource_access_with_admin(self):
        """Test that admin users can access any resource."""
        admin_id = uuid.uuid4()
        admin_user = User(id=admin_id, username="admin", email="admin@test.com", hashed_password="hash", is_admin=True)
        
        other_user_id = uuid.uuid4()
        resource = MockResource(user_id=other_user_id)
        
        result = check_resource_access(resource, admin_user)
        assert result == resource

    def test_check_resource_access_denied(self):
        """Test that non-owners cannot access resources."""
        user_id = uuid.uuid4()
        user = User(id=user_id, username="user", email="user@test.com", hashed_password="hash", is_admin=False)
        
        other_user_id = uuid.uuid4()
        resource = MockResource(user_id=other_user_id)
        
        with pytest.raises(HTTPException) as exc_info:
            check_resource_access(resource, user)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND  # Returns 404 to avoid leaking existence

    def test_check_resource_access_not_found(self):
        """Test that None resources return 404."""
        user_id = uuid.uuid4()
        user = User(id=user_id, username="user", email="user@test.com", hashed_password="hash", is_admin=False)
        
        with pytest.raises(HTTPException) as exc_info:
            check_resource_access(None, user)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_check_resource_access_legacy_null_user_id(self):
        """Test that legacy resources with null user_id are accessible."""
        user_id = uuid.uuid4()
        user = User(id=user_id, username="user", email="user@test.com", hashed_password="hash", is_admin=False)
        
        # Create a resource without user_id (legacy data)
        legacy_resource = MockResource(user_id=None)
        
        result = check_resource_access(legacy_resource, user)
        assert result == legacy_resource

    def test_check_resource_write_access_delegates_to_read_access(self):
        """Test that write access check delegates to read access check."""
        user_id = uuid.uuid4()
        user = User(id=user_id, username="user", email="user@test.com", hashed_password="hash", is_admin=False)
        resource = MockResource(user_id=user_id)
        
        result = check_resource_write_access(resource, user)
        assert result == resource

    def test_admin_override_disabled(self):
        """Test that admin override can be disabled."""
        admin_id = uuid.uuid4()
        admin_user = User(id=admin_id, username="admin", email="admin@test.com", hashed_password="hash", is_admin=True)
        
        other_user_id = uuid.uuid4()
        resource = MockResource(user_id=other_user_id)
        
        with pytest.raises(HTTPException) as exc_info:
            check_resource_access(resource, admin_user, allow_admin_override=False)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_custom_error_messages(self):
        """Test custom error messages."""
        user_id = uuid.uuid4()
        user = User(id=user_id, username="user", email="user@test.com", hashed_password="hash", is_admin=False)
        
        with pytest.raises(HTTPException) as exc_info:
            check_resource_access(
                None, 
                user, 
                not_found_message="Custom not found message"
            )
        
        assert exc_info.value.detail == "Custom not found message"