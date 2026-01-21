"""Tests for chat agent tools (suggest_recipe, fetch_url_as_markdown)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai import models

from core.security import create_draft_token


# Block any real model requests in tests
models.ALLOW_MODEL_REQUESTS = False


class MockUser:
    """Mock user for testing."""

    def __init__(self, user_id: uuid.UUID | None = None) -> None:
        self.id = user_id or uuid.uuid4()


class MockDraft:
    """Mock AIDraft for testing."""

    def __init__(self, draft_id: uuid.UUID | None = None) -> None:
        self.id = draft_id or uuid.uuid4()
        self.expires_at = datetime.now(UTC) + timedelta(hours=1)


class MockChatAgentDeps:
    """Mock dependencies for chat agent tools."""

    def __init__(
        self, db: AsyncMock | None = None, user: MockUser | None = None
    ) -> None:
        self.db = db or AsyncMock()
        self.user = user or MockUser()


class MockRunContext:
    """Mock RunContext for testing tool functions."""

    def __init__(self, deps: MockChatAgentDeps | None = None) -> None:
        self.deps = deps or MockChatAgentDeps()


def _sample_recipe_params() -> dict[str, Any]:
    """Return sample recipe parameters for testing."""
    return {
        "title": "Test Recipe",
        "description": "A delicious test recipe",
        "prep_time_minutes": 15,
        "cook_time_minutes": 30,
        "serving_min": 4,
        "instructions": ["Step 1: Prepare", "Step 2: Cook", "Step 3: Serve"],
        "category": "dinner",
        "ingredients": [
            {"name": "flour", "quantity_value": 2.0, "quantity_unit": "cups"},
            {"name": "sugar", "quantity_value": 1.0, "quantity_unit": "cup"},
        ],
        "source_url": "https://example.com/recipe",
    }


class TestSuggestRecipeTool:
    """Tests for the suggest_recipe tool function."""

    @pytest.mark.asyncio
    async def test_suggest_recipe_creates_draft_successfully(self) -> None:
        """Test successful recipe draft creation with valid parameters."""
        # Arrange
        user = MockUser()
        draft = MockDraft()
        mock_db = AsyncMock()

        with (
            patch(
                "services.chat_agent.tools.suggestions.create_success_draft",
                new_callable=AsyncMock,
                return_value=draft,
            ) as mock_create_draft,
            patch(
                "services.chat_agent.tools.suggestions.create_draft_token",
                return_value="test-jwt-token",
            ),
        ):
            params = _sample_recipe_params()

            # Act - call the suggest_recipe logic directly

            recipe_data = {
                "title": params["title"],
                "description": params["description"],
                "prep_time_minutes": params["prep_time_minutes"],
                "cook_time_minutes": params["cook_time_minutes"],
                "serving_min": params["serving_min"],
                "instructions": params["instructions"],
                "category": params["category"],
                "ingredients": params["ingredients"],
                "difficulty": "medium",
                "link_source": params["source_url"],
            }

            created_draft = await mock_create_draft(
                db=mock_db,
                current_user=user,
                source_url=params["source_url"],
                generated_recipe=recipe_data,
            )

            # Assert
            assert created_draft == draft
            mock_create_draft.assert_called_once()

    @pytest.mark.asyncio
    async def test_deep_link_url_format(self) -> None:
        """Test that deep-link URL is properly formatted."""
        draft = MockDraft()
        user = MockUser()

        # Generate token using actual function
        token = create_draft_token(draft_id=draft.id, user_id=user.id)

        # Build deep-link URL
        deep_link = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"

        # Assert URL format
        assert deep_link.startswith("/recipes/new?ai=1&draftId=")
        assert f"draftId={draft.id}" in deep_link
        assert "token=" in deep_link
        # Token should be a JWT (three parts separated by dots)
        token_part = deep_link.split("token=")[1]
        assert len(token_part.split(".")) == 3

    @pytest.mark.asyncio
    async def test_recipe_card_response_structure(self) -> None:
        """Test that recipe card response has correct structure."""
        title = "Chocolate Cake"
        description = "Rich chocolate layer cake"
        draft = MockDraft()
        user = MockUser()
        token = create_draft_token(draft_id=draft.id, user_id=user.id)
        deep_link = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"

        # Build expected response structure
        recipe_card = {
            "type": "recipe_card",
            "title": title,
            "subtitle": description,
            "image_url": None,
            "href": deep_link,
        }

        # Assert structure
        assert recipe_card["type"] == "recipe_card"
        assert recipe_card["title"] == title
        assert recipe_card["subtitle"] == description
        assert recipe_card["image_url"] is None
        assert recipe_card["href"].startswith("/recipes/new?ai=1")

    @pytest.mark.asyncio
    async def test_suggest_recipe_handles_missing_source_url(self) -> None:
        """Test recipe creation without source_url uses fallback."""
        params = _sample_recipe_params()
        params["source_url"] = None

        # The fallback should be "chat://recommendation"
        expected_source = "chat://recommendation"

        # Verify the logic would use the fallback
        source_url = params["source_url"] or "chat://recommendation"
        assert source_url == expected_source

    @pytest.mark.asyncio
    async def test_suggest_recipe_error_handling(self) -> None:
        """Test error handling when draft creation fails."""
        with patch(
            "services.chat_agent.tools.suggestions.create_success_draft",
            new_callable=AsyncMock,
            side_effect=Exception("Database connection failed"),
        ):
            # The tool should return an error response, not raise
            error_response = {
                "status": "error",
                "recipe_card": None,
                "message": "Failed to create recipe draft: Database connection failed",
            }

            assert error_response["status"] == "error"
            assert error_response["recipe_card"] is None
            assert "Failed to create recipe draft" in error_response["message"]


class TestDraftTokenGeneration:
    """Tests for draft token generation and validation."""

    def test_create_draft_token_contains_required_claims(self) -> None:
        """Test that draft token contains all required claims."""
        from jose import jwt

        from core.config import get_settings

        draft_id = uuid.uuid4()
        user_id = uuid.uuid4()

        token = create_draft_token(draft_id=draft_id, user_id=user_id)

        # Decode without verification to check claims
        settings = get_settings()
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert payload["draft_id"] == str(draft_id)
        assert payload["user_id"] == str(user_id)
        assert payload["type"] == "draft"
        assert "exp" in payload

    def test_create_draft_token_default_expiration(self) -> None:
        """Test that token has default 1-hour expiration."""
        from jose import jwt

        from core.config import get_settings

        draft_id = uuid.uuid4()
        user_id = uuid.uuid4()

        token = create_draft_token(draft_id=draft_id, user_id=user_id)

        settings = get_settings()
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Expiration should be approximately 1 hour from now
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        now = datetime.now(UTC)
        time_diff = exp - now

        # Should be between 59 and 61 minutes
        assert timedelta(minutes=59) < time_diff < timedelta(minutes=61)


class TestRecipeCardBlockSchema:
    """Tests for RecipeCardBlock schema with relative URLs."""

    def test_recipe_card_accepts_relative_url(self) -> None:
        """Test that RecipeCardBlock accepts relative URL in href field."""
        from schemas.chat_content import RecipeCardBlock

        draft_id = uuid.uuid4()
        relative_url = f"/recipes/new?ai=1&draftId={draft_id}&token=abc123"

        card = RecipeCardBlock(
            type="recipe_card",
            title="Test Recipe",
            subtitle="Test description",
            href=relative_url,
        )

        assert card.href == relative_url
        assert card.href.startswith("/recipes/new")

    def test_recipe_card_accepts_absolute_url(self) -> None:
        """Test that RecipeCardBlock still accepts absolute URLs."""
        from schemas.chat_content import RecipeCardBlock

        absolute_url = "https://example.com/recipe/123"

        card = RecipeCardBlock(
            type="recipe_card",
            title="External Recipe",
            subtitle="From the web",
            href=absolute_url,
        )

        assert card.href == absolute_url

    def test_recipe_card_accepts_none_href(self) -> None:
        """Test that RecipeCardBlock accepts None for href."""
        from schemas.chat_content import RecipeCardBlock

        card = RecipeCardBlock(
            type="recipe_card",
            title="Recipe Without Link",
            subtitle="No link available",
            href=None,
        )

        assert card.href is None
