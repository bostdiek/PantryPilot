"""Integration tests for the feedback API endpoint.

These tests mock the database layer to test the API contract (request/response)
and authentication requirements.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from dependencies.auth import get_current_user
from dependencies.db import get_db
from main import app
from models.users import User


def _make_mock_user(user_id: uuid.UUID | None = None) -> User:
    """Create a mock user object."""
    uid = user_id or uuid.uuid4()
    user = MagicMock(spec=User)
    user.id = uid
    user.username = "testuser"
    user.email = "testuser@example.com"
    return user


def _make_mock_training_sample(
    sample_id: uuid.UUID,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    user_feedback: str | None = None,
) -> SimpleNamespace:
    """Create a mock training sample object."""
    return SimpleNamespace(
        id=sample_id,
        message_id=message_id,
        user_id=user_id,
        user_feedback=user_feedback,
    )


class MockResult:
    """Mock SQLAlchemy result object."""

    def __init__(self, value: object | None = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value


@pytest_asyncio.fixture
async def mock_client() -> AsyncGenerator[tuple[AsyncClient, AsyncMock, User], None]:
    """Create a test client with mocked dependencies."""
    mock_db = AsyncMock()
    mock_user = _make_mock_user()

    # Override dependencies
    original_db = app.dependency_overrides.get(get_db)
    original_auth = app.dependency_overrides.get(get_current_user)

    async def _override_db() -> AsyncGenerator[AsyncMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, mock_db, mock_user

    # Restore original dependencies
    if original_db:
        app.dependency_overrides[get_db] = original_db
    else:
        app.dependency_overrides.pop(get_db, None)

    if original_auth:
        app.dependency_overrides[get_current_user] = original_auth
    else:
        app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def unauthenticated_client() -> AsyncGenerator[AsyncClient, None]:
    """Create a test client without auth override (to test 401)."""
    mock_db = AsyncMock()

    # Only override database, not auth
    original_db = app.dependency_overrides.get(get_db)
    original_auth = app.dependency_overrides.pop(get_current_user, None)

    async def _override_db() -> AsyncGenerator[AsyncMock, None]:
        yield mock_db

    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    # Restore dependencies
    if original_db:
        app.dependency_overrides[get_db] = original_db
    else:
        app.dependency_overrides.pop(get_db, None)

    if original_auth:
        app.dependency_overrides[get_current_user] = original_auth


class TestFeedbackAPI:
    """Test feedback API endpoints."""

    @pytest.mark.asyncio
    async def test_submit_positive_feedback(
        self, mock_client: tuple[AsyncClient, AsyncMock, User]
    ) -> None:
        """Test submitting positive feedback for a message."""
        client, mock_db, mock_user = mock_client
        msg_id = uuid.uuid4()
        sample_id = uuid.uuid4()

        # Create mock training sample
        mock_sample = _make_mock_training_sample(
            sample_id=sample_id,
            message_id=msg_id,
            user_id=mock_user.id,
        )

        # Configure mock to return sample on query
        mock_db.execute.return_value = MockResult(mock_sample)

        response = await client.post(
            f"/api/v1/messages/{msg_id}/feedback",
            json={"user_feedback": "positive"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["feedback"] == "positive"
        assert data["message_id"] == str(msg_id)

        # Verify feedback was updated on sample
        assert mock_sample.user_feedback == "positive"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_negative_feedback(
        self, mock_client: tuple[AsyncClient, AsyncMock, User]
    ) -> None:
        """Test submitting negative feedback for a message."""
        client, mock_db, mock_user = mock_client
        msg_id = uuid.uuid4()
        sample_id = uuid.uuid4()

        mock_sample = _make_mock_training_sample(
            sample_id=sample_id,
            message_id=msg_id,
            user_id=mock_user.id,
        )
        mock_db.execute.return_value = MockResult(mock_sample)

        response = await client.post(
            f"/api/v1/messages/{msg_id}/feedback",
            json={"user_feedback": "negative"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["feedback"] == "negative"
        assert mock_sample.user_feedback == "negative"

    @pytest.mark.asyncio
    async def test_feedback_requires_authentication(
        self, unauthenticated_client: AsyncClient
    ) -> None:
        """Test that feedback endpoint requires authentication."""
        client = unauthenticated_client
        random_msg_id = uuid.uuid4()

        response = await client.post(
            f"/api/v1/messages/{random_msg_id}/feedback",
            json={"user_feedback": "positive"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_feedback_message_not_found(
        self, mock_client: tuple[AsyncClient, AsyncMock, User]
    ) -> None:
        """Test feedback returns 404 when message has no training sample."""
        client, mock_db, _ = mock_client
        random_msg_id = uuid.uuid4()

        # Configure mock to return no result
        mock_db.execute.return_value = MockResult(None)

        response = await client.post(
            f"/api/v1/messages/{random_msg_id}/feedback",
            json={"user_feedback": "positive"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Training sample not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_feedback_invalid_value(
        self, mock_client: tuple[AsyncClient, AsyncMock, User]
    ) -> None:
        """Test feedback validation rejects invalid feedback values."""
        client, _, _ = mock_client
        msg_id = uuid.uuid4()

        # Validation happens before database query, so no mock setup needed
        response = await client.post(
            f"/api/v1/messages/{msg_id}/feedback",
            json={"user_feedback": "invalid_value"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_feedback_updates_existing_feedback(
        self, mock_client: tuple[AsyncClient, AsyncMock, User]
    ) -> None:
        """Test that feedback can be updated from positive to negative."""
        client, mock_db, mock_user = mock_client
        msg_id = uuid.uuid4()
        sample_id = uuid.uuid4()

        # Sample already has positive feedback
        mock_sample = _make_mock_training_sample(
            sample_id=sample_id,
            message_id=msg_id,
            user_id=mock_user.id,
            user_feedback="positive",
        )
        mock_db.execute.return_value = MockResult(mock_sample)

        # Update to negative
        response = await client.post(
            f"/api/v1/messages/{msg_id}/feedback",
            json={"user_feedback": "negative"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["feedback"] == "negative"
        assert mock_sample.user_feedback == "negative"
