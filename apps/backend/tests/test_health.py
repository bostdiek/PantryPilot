"""Tests for health check endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app


class TestHealthCheck:
    """Tests for basic health check endpoint."""

    def test_health_check_returns_success(self) -> None:
        """Test basic health check returns healthy status."""
        client = TestClient(app)
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
        assert "SmartMealPlanner" in data["data"]["message"]
        assert data["message"] == "Health check successful"

    def test_health_check_response_structure(self) -> None:
        """Test health check response matches ApiResponse schema."""
        client = TestClient(app)
        response = client.get("/api/v1/health")

        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "message" in data
        assert isinstance(data["data"], dict)
        assert "status" in data["data"]


@pytest.mark.asyncio
class TestEmbeddingHealthCheck:
    """Tests for embedding model health check endpoint."""

    @pytest_asyncio.fixture
    async def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @patch("api.v1.health.get_settings")
    async def test_embedding_health_all_current(
        self, mock_settings: MagicMock, mock_db: AsyncMock
    ) -> None:
        """Test when all embeddings use current model."""
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-004"

        # Mock total embeddings count
        total_result = MagicMock()
        total_result.scalar.return_value = 100

        # Mock current model count
        current_result = MagicMock()
        current_result.scalar.return_value = 100

        # Mock legacy count
        legacy_result = MagicMock()
        legacy_result.scalar.return_value = 0

        mock_db.execute.side_effect = [total_result, current_result, legacy_result]

        from api.v1.health import embedding_health_check

        response = await embedding_health_check(db=mock_db)

        assert response.success is True
        assert response.data["current_model"] == "text-embedding-004"
        assert response.data["total_with_embeddings"] == 100
        assert response.data["current_model_count"] == 100
        assert response.data["legacy_count"] == 0
        assert response.data["outdated_count"] == 0
        assert response.data["needs_update"] is False

    @patch("api.v1.health.get_settings")
    async def test_embedding_health_with_outdated(
        self,
        mock_settings: MagicMock,
        mock_db: AsyncMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test when some embeddings use outdated models."""
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-004"

        # Total: 100, Current: 60, Legacy: 10 = Outdated: 30
        total_result = MagicMock()
        total_result.scalar.return_value = 100

        current_result = MagicMock()
        current_result.scalar.return_value = 60

        legacy_result = MagicMock()
        legacy_result.scalar.return_value = 10

        mock_db.execute.side_effect = [total_result, current_result, legacy_result]

        from api.v1.health import embedding_health_check

        response = await embedding_health_check(db=mock_db)

        assert response.success is True
        assert response.data["total_with_embeddings"] == 100
        assert response.data["current_model_count"] == 60
        assert response.data["legacy_count"] == 10
        assert response.data["outdated_count"] == 30
        assert response.data["needs_update"] is True

        # Check warning was logged
        assert "mismatch detected" in caplog.text.lower()
        assert "30 outdated" in caplog.text

    @patch("api.v1.health.get_settings")
    async def test_embedding_health_with_legacy_only(
        self,
        mock_settings: MagicMock,
        mock_db: AsyncMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test when embeddings have no model tracking (legacy)."""
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-004"

        total_result = MagicMock()
        total_result.scalar.return_value = 50

        current_result = MagicMock()
        current_result.scalar.return_value = 0

        legacy_result = MagicMock()
        legacy_result.scalar.return_value = 50

        mock_db.execute.side_effect = [total_result, current_result, legacy_result]

        from api.v1.health import embedding_health_check

        response = await embedding_health_check(db=mock_db)

        assert response.data["total_with_embeddings"] == 50
        assert response.data["current_model_count"] == 0
        assert response.data["legacy_count"] == 50
        assert response.data["outdated_count"] == 0
        assert response.data["needs_update"] is True

        # Check warning about legacy embeddings
        assert "50 legacy" in caplog.text

    @patch("api.v1.health.get_settings")
    async def test_embedding_health_with_no_embeddings(
        self, mock_settings: MagicMock, mock_db: AsyncMock
    ) -> None:
        """Test when no recipes have embeddings yet."""
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-004"

        total_result = MagicMock()
        total_result.scalar.return_value = 0

        current_result = MagicMock()
        current_result.scalar.return_value = 0

        legacy_result = MagicMock()
        legacy_result.scalar.return_value = 0

        mock_db.execute.side_effect = [total_result, current_result, legacy_result]

        from api.v1.health import embedding_health_check

        response = await embedding_health_check(db=mock_db)

        assert response.data["total_with_embeddings"] == 0
        assert response.data["current_model_count"] == 0
        assert response.data["legacy_count"] == 0
        assert response.data["outdated_count"] == 0
        assert response.data["needs_update"] is False

    @patch("api.v1.health.get_settings")
    async def test_embedding_health_with_null_counts(
        self, mock_settings: MagicMock, mock_db: AsyncMock
    ) -> None:
        """Test handles None return from scalar() gracefully."""
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-004"

        # Simulate None returns from scalar()
        total_result = MagicMock()
        total_result.scalar.return_value = None

        current_result = MagicMock()
        current_result.scalar.return_value = None

        legacy_result = MagicMock()
        legacy_result.scalar.return_value = None

        mock_db.execute.side_effect = [total_result, current_result, legacy_result]

        from api.v1.health import embedding_health_check

        response = await embedding_health_check(db=mock_db)

        # Should default to 0 when None
        assert response.data["total_with_embeddings"] == 0
        assert response.data["current_model_count"] == 0
        assert response.data["legacy_count"] == 0
        assert response.data["outdated_count"] == 0

    @patch("api.v1.health.get_settings")
    async def test_embedding_health_message_content(
        self, mock_settings: MagicMock, mock_db: AsyncMock
    ) -> None:
        """Test response message is appropriate."""
        mock_settings.return_value.EMBEDDING_MODEL = "text-embedding-004"

        total_result = MagicMock()
        total_result.scalar.return_value = 10

        current_result = MagicMock()
        current_result.scalar.return_value = 10

        legacy_result = MagicMock()
        legacy_result.scalar.return_value = 0

        mock_db.execute.side_effect = [total_result, current_result, legacy_result]

        from api.v1.health import embedding_health_check

        response = await embedding_health_check(db=mock_db)

        assert response.message == "Embedding health check complete"
        assert response.success is True
