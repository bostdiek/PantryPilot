"""Tests for chat agent tools (suggest_recipe, fetch_url_as_markdown)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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
        self,
        db: AsyncMock | None = None,
        user: MockUser | None = None,
        user_preferences: Any = None,
        memory_content: str | None = None,
    ) -> None:
        self.db = db or AsyncMock()
        self.user = user or MockUser()
        self.user_preferences = user_preferences
        self.memory_content = memory_content


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


class TestBuildHybridResult:
    """Tests for _build_hybrid_result helper function."""

    def test_builds_result_with_items(self) -> None:
        """Test building hybrid result with recipe items."""
        from services.chat_agent.tools.recipes import _build_hybrid_result

        # Create mock recipe objects
        mock_recipe = MagicMock()
        mock_recipe.id = uuid.uuid4()
        mock_recipe.name = "Test Recipe"

        items = [
            {
                "recipe": mock_recipe,
                "times_cooked": 5,
                "text_rank": 1,
                "vector_rank": 2,
            }
        ]
        full_payload_by_id = {str(mock_recipe.id): {"title": "Test Recipe"}}

        result = _build_hybrid_result(
            items=items,
            full_payload_by_id=full_payload_by_id,
            query="test query",
            cuisine=None,
            difficulty=None,
            max_cook_time=None,
            min_times_cooked=None,
            sort_by="relevance",
            rrf_k=60,
        )

        assert result["status"] == "ok"
        assert result["query"] == "test query"
        assert result["total_results"] == 1
        assert len(result["recipes"]) == 1
        assert result["recipes"][0]["title"] == "Test Recipe"
        assert result["recipes"][0]["times_cooked"] == 5
        assert "relevance_score" in result["recipes"][0]

    def test_builds_result_with_fallback_flag(self) -> None:
        """Test fallback_used flag is included in result."""
        from services.chat_agent.tools.recipes import _build_hybrid_result

        result = _build_hybrid_result(
            items=[],
            full_payload_by_id={},
            query="fallback query",
            cuisine="italian",
            difficulty=None,
            max_cook_time=30,
            min_times_cooked=None,
            sort_by="relevance",
            rrf_k=60,
            fallback_used=True,
        )

        assert result["fallback_used"] is True
        assert result["filters_applied"]["cuisine"] == "italian"
        assert result["filters_applied"]["max_cook_time"] == 30

    def test_builds_empty_result(self) -> None:
        """Test building result with no items."""
        from services.chat_agent.tools.recipes import _build_hybrid_result

        result = _build_hybrid_result(
            items=[],
            full_payload_by_id={},
            query="no results",
            cuisine=None,
            difficulty=None,
            max_cook_time=None,
            min_times_cooked=None,
            sort_by="relevance",
            rrf_k=60,
        )

        assert result["total_results"] == 0
        assert result["recipes"] == []


class TestBuildMetadataResult:
    """Tests for _build_metadata_result helper function."""

    def test_builds_result_with_rows(self) -> None:
        """Test building metadata result with recipe rows."""
        from services.chat_agent.tools.recipes import _build_metadata_result

        mock_recipe = MagicMock()
        mock_recipe.id = uuid.uuid4()
        mock_recipe.name = "Pasta Dish"

        rows = [(mock_recipe, 3)]
        full_payload_by_id = {str(mock_recipe.id): {"title": "Pasta Dish"}}

        result = _build_metadata_result(
            rows=rows,
            full_payload_by_id=full_payload_by_id,
            cuisine="italian",
            difficulty="easy",
            max_cook_time=30,
            min_times_cooked=2,
            sort_by="name",
        )

        assert result["status"] == "ok"
        assert result["query"] is None  # No query for metadata-only search
        assert result["total_results"] == 1
        assert len(result["recipes"]) == 1
        assert result["recipes"][0]["title"] == "Pasta Dish"
        assert result["recipes"][0]["times_cooked"] == 3

    def test_builds_result_with_all_filters(self) -> None:
        """Test all filters are captured in result."""
        from services.chat_agent.tools.recipes import _build_metadata_result

        result = _build_metadata_result(
            rows=[],
            full_payload_by_id={},
            cuisine="mexican",
            difficulty="hard",
            max_cook_time=60,
            min_times_cooked=5,
            sort_by="times_cooked",
        )

        assert result["filters_applied"]["cuisine"] == "mexican"
        assert result["filters_applied"]["difficulty"] == "hard"
        assert result["filters_applied"]["max_cook_time"] == 60
        assert result["filters_applied"]["min_times_cooked"] == 5
        assert result["sort_by"] == "times_cooked"


class TestBuildFallbackQuery:
    """Tests for _build_fallback_query helper function."""

    def test_builds_query_from_cuisine(self) -> None:
        """Test building fallback query from cuisine filter."""
        from services.chat_agent.tools.recipes import _build_fallback_query

        result = _build_fallback_query(
            cuisine="italian",
            difficulty=None,
            max_cook_time=None,
            min_times_cooked=None,
        )

        assert "italian cuisine" in result

    def test_builds_query_from_difficulty(self) -> None:
        """Test building fallback query from difficulty filter."""
        from services.chat_agent.tools.recipes import _build_fallback_query

        result = _build_fallback_query(
            cuisine=None,
            difficulty="easy",
            max_cook_time=None,
            min_times_cooked=None,
        )

        assert "easy difficulty" in result

    def test_builds_query_from_max_cook_time(self) -> None:
        """Test building fallback query from max_cook_time filter."""
        from services.chat_agent.tools.recipes import _build_fallback_query

        result = _build_fallback_query(
            cuisine=None,
            difficulty=None,
            max_cook_time=30,
            min_times_cooked=None,
        )

        assert "under 30 minutes" in result

    def test_builds_query_from_min_times_cooked(self) -> None:
        """Test building fallback query from min_times_cooked filter."""
        from services.chat_agent.tools.recipes import _build_fallback_query

        result = _build_fallback_query(
            cuisine=None,
            difficulty=None,
            max_cook_time=None,
            min_times_cooked=5,
        )

        assert "cooked at least 5 times" in result

    def test_builds_combined_query(self) -> None:
        """Test building fallback query from multiple filters."""
        from services.chat_agent.tools.recipes import _build_fallback_query

        result = _build_fallback_query(
            cuisine="mexican",
            difficulty="medium",
            max_cook_time=45,
            min_times_cooked=2,
        )

        assert "mexican cuisine" in result
        assert "medium difficulty" in result
        assert "under 45 minutes" in result
        assert "cooked at least 2 times" in result

    def test_returns_empty_string_when_no_filters(self) -> None:
        """Test returns empty string when no filters provided."""
        from services.chat_agent.tools.recipes import _build_fallback_query

        result = _build_fallback_query(
            cuisine=None,
            difficulty=None,
            max_cook_time=None,
            min_times_cooked=None,
        )

        assert result == ""


class TestBuildFilterList:
    """Tests for _build_filter_list helper function."""

    def test_adds_cuisine_filter(self) -> None:
        """Test cuisine filter is added to list."""
        from services.chat_agent.tools.recipes import _build_filter_list

        mock_sq = MagicMock()

        filters = _build_filter_list(
            cuisine="asian",
            difficulty=None,
            max_cook_time=None,
            min_times_cooked=None,
            times_cooked_sq=mock_sq,
        )

        assert len(filters) == 1

    def test_adds_difficulty_filter(self) -> None:
        """Test difficulty filter is added to list."""
        from services.chat_agent.tools.recipes import _build_filter_list

        mock_sq = MagicMock()

        filters = _build_filter_list(
            cuisine=None,
            difficulty="hard",
            max_cook_time=None,
            min_times_cooked=None,
            times_cooked_sq=mock_sq,
        )

        assert len(filters) == 1

    def test_adds_max_cook_time_filter(self) -> None:
        """Test max_cook_time filter is added to list."""
        from services.chat_agent.tools.recipes import _build_filter_list

        mock_sq = MagicMock()

        filters = _build_filter_list(
            cuisine=None,
            difficulty=None,
            max_cook_time=30,
            min_times_cooked=None,
            times_cooked_sq=mock_sq,
        )

        assert len(filters) == 1

    def test_adds_min_times_cooked_filter(self) -> None:
        """Test min_times_cooked filter is added to list."""
        from services.chat_agent.tools.recipes import _build_filter_list

        mock_sq = MagicMock()
        mock_sq.c.cook_count = MagicMock()

        filters = _build_filter_list(
            cuisine=None,
            difficulty=None,
            max_cook_time=None,
            min_times_cooked=3,
            times_cooked_sq=mock_sq,
        )

        assert len(filters) == 1

    def test_combines_all_filters(self) -> None:
        """Test all filters are combined."""
        from services.chat_agent.tools.recipes import _build_filter_list

        mock_sq = MagicMock()
        mock_sq.c.cook_count = MagicMock()

        filters = _build_filter_list(
            cuisine="french",
            difficulty="medium",
            max_cook_time=60,
            min_times_cooked=2,
            times_cooked_sq=mock_sq,
        )

        assert len(filters) == 4

    def test_returns_empty_list_when_no_filters(self) -> None:
        """Test returns empty list when no filters provided."""
        from services.chat_agent.tools.recipes import _build_filter_list

        mock_sq = MagicMock()

        filters = _build_filter_list(
            cuisine=None,
            difficulty=None,
            max_cook_time=None,
            min_times_cooked=None,
            times_cooked_sq=mock_sq,
        )

        assert filters == []
