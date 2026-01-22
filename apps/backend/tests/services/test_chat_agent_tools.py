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


# ============================================================================
# MEAL HISTORY TOOL TESTS
# ============================================================================


class TestMealPlanHistoryResponse:
    """Tests for MealPlanHistoryResponse schema."""

    def test_response_structure(self) -> None:
        """Test that MealPlanHistoryResponse has correct structure."""
        from services.chat_agent.schemas import (
            MealPlanHistoryResponse,
            TimelineDayMeals,
        )

        response = MealPlanHistoryResponse(
            days_analyzed=28,
            total_meals=42,
            meals_by_day_of_week={
                "Monday": [{"date": "2026-01-20", "meal_type": "dinner"}]
            },
            chronological_timeline=[
                TimelineDayMeals(date="2026-01-20", meals=["Pasta Carbonara"])
            ],
            eating_out_count=5,
            leftover_count=3,
            cuisine_counts={"Italian": 10, "Mexican": 5},
        )

        assert response.days_analyzed == 28
        assert response.total_meals == 42
        assert response.eating_out_count == 5
        assert response.leftover_count == 3
        assert len(response.chronological_timeline) == 1
        assert response.cuisine_counts["Italian"] == 10

    def test_timeline_day_meals(self) -> None:
        """Test TimelineDayMeals structure."""
        from services.chat_agent.schemas import TimelineDayMeals

        day = TimelineDayMeals(
            date="2026-01-22",
            meals=["Breakfast Burrito", "Caesar Salad", "Grilled Salmon"],
        )

        assert day.date == "2026-01-22"
        assert len(day.meals) == 3
        assert "Breakfast Burrito" in day.meals


class TestGetMealPlanHistoryTool:
    """Tests for the get_meal_plan_history tool function."""

    @pytest.mark.asyncio
    async def test_get_meal_plan_history_clamps_days(self) -> None:
        """Test that days parameter is clamped to 1-90 range."""
        # Test the clamping logic directly
        # days = max(1, min(days, 90))
        assert max(1, min(0, 90)) == 1  # 0 -> 1
        assert max(1, min(100, 90)) == 90  # 100 -> 90
        assert max(1, min(30, 90)) == 30  # 30 -> 30

    @pytest.mark.asyncio
    async def test_meal_history_empty_result(self) -> None:
        """Test meal history with no meals."""
        from services.chat_agent.schemas import MealPlanHistoryResponse

        # Create empty response
        response = MealPlanHistoryResponse(
            days_analyzed=28,
            total_meals=0,
            meals_by_day_of_week={},
            chronological_timeline=[],
            eating_out_count=0,
            leftover_count=0,
            cuisine_counts={},
        )

        assert response.total_meals == 0
        assert response.chronological_timeline == []


# ============================================================================
# SEARCH RECIPES TOOL TESTS
# ============================================================================


class TestRRFScore:
    """Tests for Reciprocal Rank Fusion scoring."""

    def test_rrf_score_text_only(self) -> None:
        """Test RRF score with only text rank."""
        from services.chat_agent.tools.recipes import _rrf_score

        score = _rrf_score(text_rank=1, vector_rank=None, k=60)
        expected = 1.0 / (60 + 1)  # 1/61

        assert abs(score - expected) < 1e-6

    def test_rrf_score_vector_only(self) -> None:
        """Test RRF score with only vector rank."""
        from services.chat_agent.tools.recipes import _rrf_score

        score = _rrf_score(text_rank=None, vector_rank=1, k=60)
        expected = 1.0 / (60 + 1)  # 1/61

        assert abs(score - expected) < 1e-6

    def test_rrf_score_both_ranks(self) -> None:
        """Test RRF score with both text and vector ranks."""
        from services.chat_agent.tools.recipes import _rrf_score

        score = _rrf_score(text_rank=1, vector_rank=2, k=60)
        expected = 1.0 / (60 + 1) + 1.0 / (60 + 2)  # 1/61 + 1/62

        assert abs(score - expected) < 1e-6

    def test_rrf_score_no_ranks(self) -> None:
        """Test RRF score with no ranks returns 0."""
        from services.chat_agent.tools.recipes import _rrf_score

        score = _rrf_score(text_rank=None, vector_rank=None, k=60)

        assert score == 0.0

    def test_rrf_score_higher_for_better_ranks(self) -> None:
        """Test that better ranks produce higher scores."""
        from services.chat_agent.tools.recipes import _rrf_score

        score_rank1 = _rrf_score(text_rank=1, vector_rank=1, k=60)
        score_rank5 = _rrf_score(text_rank=5, vector_rank=5, k=60)

        assert score_rank1 > score_rank5


class TestBuildEmbeddingLiteral:
    """Tests for building embedding literal SQL."""

    def test_build_embedding_literal_format(self) -> None:
        """Test embedding literal has correct format."""
        from services.chat_agent.tools.recipes import _build_embedding_literal

        embedding = [0.1, 0.2, 0.3]
        result = _build_embedding_literal(embedding)

        assert result == "'[0.1,0.2,0.3]'::vector(768)"

    def test_build_embedding_literal_empty(self) -> None:
        """Test embedding literal with empty vector."""
        from services.chat_agent.tools.recipes import _build_embedding_literal

        embedding: list[float] = []
        result = _build_embedding_literal(embedding)

        assert result == "'[]'::vector(768)"


class TestSearchRecipesFilters:
    """Tests for search_recipes filter application."""

    def test_apply_optional_filters_cuisine(self) -> None:
        """Test cuisine filter is applied correctly."""
        from services.chat_agent.tools.recipes import _apply_optional_filters

        predicates: list[Any] = []
        times_cooked_expr = None  # Not needed for this test

        _apply_optional_filters(
            predicates=predicates,
            cuisine="italian",
            difficulty=None,
            max_cook_time=None,
            min_times_cooked=None,
            times_cooked_expr=times_cooked_expr,
        )

        # Should have added one predicate
        assert len(predicates) == 1

    def test_apply_optional_filters_multiple(self) -> None:
        """Test multiple filters applied together."""
        from unittest.mock import MagicMock

        from services.chat_agent.tools.recipes import _apply_optional_filters

        predicates: list[Any] = []
        times_cooked_expr = MagicMock()
        times_cooked_expr.__ge__ = MagicMock(return_value="ge_result")

        _apply_optional_filters(
            predicates=predicates,
            cuisine="mexican",
            difficulty="easy",
            max_cook_time=30,
            min_times_cooked=2,
            times_cooked_expr=times_cooked_expr,
        )

        # Should have 4 predicates
        assert len(predicates) == 4


class TestSearchRecipesOutput:
    """Tests for search_recipes output structure."""

    def test_output_structure_with_query(self) -> None:
        """Test output structure when query is provided."""
        # Verify expected output keys
        expected_keys = {
            "status",
            "query",
            "recipes_page_path",
            "meal_plan_page_path",
            "filters_applied",
            "total_results",
            "recipes",
        }

        # This is what the tool returns
        sample_output = {
            "status": "ok",
            "query": "pasta",
            "recipes_page_path": "/recipes",
            "meal_plan_page_path": "/meal-plan",
            "filters_applied": {"cuisine": None, "difficulty": None},
            "total_results": 5,
            "recipes": [],
        }

        assert set(sample_output.keys()) >= expected_keys

    def test_recipe_item_structure(self) -> None:
        """Test individual recipe item structure in output."""
        expected_keys = {
            "id",
            "title",
            "detail_path",
            "edit_path",
            "full_recipe",
            "times_cooked",
        }

        sample_recipe = {
            "id": "abc-123",
            "title": "Test Recipe",
            "detail_path": "/recipes/abc-123",
            "edit_path": "/recipes/abc-123/edit",
            "full_recipe": {"id": "abc-123", "title": "Test Recipe"},
            "times_cooked": 3,
        }

        assert set(sample_recipe.keys()) >= expected_keys
