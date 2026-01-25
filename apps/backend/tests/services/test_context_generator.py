"""Tests for the context generator service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import models


# Block any real model requests in tests
models.ALLOW_MODEL_REQUESTS = False


class MockIngredient:
    """Mock Ingredient model."""

    def __init__(self, name: str) -> None:
        self.ingredient_name = name


class MockRecipeIngredient:
    """Mock RecipeIngredient model."""

    def __init__(self, name: str) -> None:
        self.ingredient = MockIngredient(name)


class MockRecipe:
    """Mock Recipe model for testing context generation."""

    def __init__(
        self,
        name: str = "Test Recipe",
        description: str | None = None,
        recipeingredients: list[MockRecipeIngredient] | None = None,
        instructions: list[str] | None = None,
        prep_time_minutes: int | None = None,
        cook_time_minutes: int | None = None,
        difficulty: str | None = None,
        course_type: str | None = None,
        ethnicity: str | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.recipeingredients = recipeingredients or []
        self.instructions = instructions or []
        self.prep_time_minutes = prep_time_minutes
        self.cook_time_minutes = cook_time_minutes
        self.difficulty = difficulty
        self.course_type = course_type
        self.ethnicity = ethnicity


# ============================================================================
# TEST CLASSES
# ============================================================================


class TestFormatRecipeContent:
    """Tests for _format_recipe_content method."""

    def test_format_with_all_fields(self) -> None:
        """Test formatting with all recipe fields populated."""
        from services.context_generator import RecipeContextGenerator

        generator = RecipeContextGenerator(api_key="test-key")
        recipe = MockRecipe(
            name="Spaghetti Carbonara",
            description="A classic Roman pasta dish",
            recipeingredients=[
                MockRecipeIngredient("spaghetti"),
                MockRecipeIngredient("bacon"),
                MockRecipeIngredient("eggs"),
                MockRecipeIngredient("parmesan"),
            ],
            instructions=["Boil pasta", "Fry bacon", "Mix eggs", "Combine"],
            prep_time_minutes=15,
            cook_time_minutes=20,
            difficulty="medium",
            course_type="dinner",
            ethnicity="Italian",
        )

        result = generator._format_recipe_content(recipe)  # type: ignore[arg-type]

        assert "Title: Spaghetti Carbonara" in result
        assert "Description: A classic Roman pasta dish" in result
        assert "spaghetti" in result
        assert "bacon" in result
        assert "Time: 15 min prep, 20 min cook" in result
        assert "Difficulty: medium" in result
        assert "Category: dinner" in result
        assert "Cuisine: Italian" in result

    def test_format_with_minimal_fields(self) -> None:
        """Test formatting with only title (minimal recipe)."""
        from services.context_generator import RecipeContextGenerator

        generator = RecipeContextGenerator(api_key="test-key")
        recipe = MockRecipe(name="Simple Recipe")

        result = generator._format_recipe_content(recipe)  # type: ignore[arg-type]

        assert "Title: Simple Recipe" in result
        # No other fields should be present
        assert "Description:" not in result
        assert "Ingredients:" not in result
        assert "Time:" not in result

    def test_format_with_partial_times(self) -> None:
        """Test formatting with only prep time (no cook time)."""
        from services.context_generator import RecipeContextGenerator

        generator = RecipeContextGenerator(api_key="test-key")
        recipe = MockRecipe(name="Quick Salad", prep_time_minutes=10)

        result = generator._format_recipe_content(recipe)  # type: ignore[arg-type]

        assert "Time: 10 min prep" in result
        assert "cook" not in result.lower()

    def test_format_truncates_long_ingredient_list(self) -> None:
        """Test that ingredient list is truncated to 20 items."""
        from services.context_generator import RecipeContextGenerator

        generator = RecipeContextGenerator(api_key="test-key")
        ingredients = [MockRecipeIngredient(f"ingredient_{i}") for i in range(25)]
        recipe = MockRecipe(name="Complex Recipe", recipeingredients=ingredients)

        result = generator._format_recipe_content(recipe)  # type: ignore[arg-type]

        # Should contain first 20 ingredients, not the last 5
        assert "ingredient_0" in result
        assert "ingredient_19" in result
        assert "ingredient_20" not in result


class TestGenerateFallbackContext:
    """Tests for _generate_fallback_context method."""

    def test_fallback_with_all_metadata(self) -> None:
        """Test fallback context with all metadata fields."""
        from services.context_generator import RecipeContextGenerator

        generator = RecipeContextGenerator(api_key="test-key")
        recipe = MockRecipe(
            name="Tacos",
            ethnicity="Mexican",
            course_type="dinner",
            difficulty="easy",
        )

        result = generator._generate_fallback_context(recipe)  # type: ignore[arg-type]

        assert "This is a Mexican recipe" in result
        assert "for dinner" in result
        assert "with easy difficulty" in result
        assert "called Tacos." in result

    def test_fallback_with_no_ethnicity(self) -> None:
        """Test fallback context without ethnicity."""
        from services.context_generator import RecipeContextGenerator

        generator = RecipeContextGenerator(api_key="test-key")
        recipe = MockRecipe(name="Mystery Dish", course_type="lunch")

        result = generator._generate_fallback_context(recipe)  # type: ignore[arg-type]

        assert "This recipe for lunch" in result
        assert "called Mystery Dish." in result

    def test_fallback_with_only_name(self) -> None:
        """Test fallback context with only recipe name."""
        from services.context_generator import RecipeContextGenerator

        generator = RecipeContextGenerator(api_key="test-key")
        recipe = MockRecipe(name="Unnamed Dish")

        result = generator._generate_fallback_context(recipe)  # type: ignore[arg-type]

        assert "This recipe" in result
        assert "called Unnamed Dish." in result


class TestGenerateContext:
    """Tests for generate_context async method."""

    @pytest.mark.asyncio
    async def test_generate_context_success(self) -> None:
        """Test successful context generation from LLM."""
        from services.context_generator import RecipeContextGenerator

        mock_response = MagicMock()
        mock_response.text = (
            "This is a classic Italian pasta dish perfect for a quick weeknight dinner."
        )

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("services.context_generator.genai.Client", return_value=mock_client):
            generator = RecipeContextGenerator(api_key="test-key")
            recipe = MockRecipe(
                name="Pasta Primavera",
                ethnicity="Italian",
                course_type="dinner",
            )

            result = await generator.generate_context(recipe)  # type: ignore[arg-type]

        assert "Italian pasta dish" in result
        assert "weeknight dinner" in result

    @pytest.mark.asyncio
    async def test_generate_context_fallback_on_empty_response(self) -> None:
        """Test fallback when LLM returns empty response."""
        from services.context_generator import RecipeContextGenerator

        mock_response = MagicMock()
        mock_response.text = None  # Empty response

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("services.context_generator.genai.Client", return_value=mock_client):
            generator = RecipeContextGenerator(api_key="test-key")
            recipe = MockRecipe(
                name="Test Recipe",
                ethnicity="Mexican",
                course_type="dinner",
            )

            result = await generator.generate_context(recipe)  # type: ignore[arg-type]

        # Should use fallback
        assert "This is a Mexican recipe" in result
        assert "called Test Recipe." in result

    @pytest.mark.asyncio
    async def test_generate_context_fallback_on_exception(self) -> None:
        """Test fallback when LLM call raises exception."""
        from services.context_generator import RecipeContextGenerator

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )

        with patch("services.context_generator.genai.Client", return_value=mock_client):
            generator = RecipeContextGenerator(api_key="test-key")
            recipe = MockRecipe(
                name="Fallback Recipe",
                difficulty="easy",
            )

            result = await generator.generate_context(recipe)  # type: ignore[arg-type]

        # Should use fallback without raising
        assert "called Fallback Recipe." in result

    @pytest.mark.asyncio
    async def test_generate_context_strips_whitespace(self) -> None:
        """Test that generated context is stripped of whitespace."""
        from services.context_generator import RecipeContextGenerator

        mock_response = MagicMock()
        mock_response.text = "  Context with leading and trailing spaces.  \n"

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("services.context_generator.genai.Client", return_value=mock_client):
            generator = RecipeContextGenerator(api_key="test-key")
            recipe = MockRecipe(name="Test")

            result = await generator.generate_context(recipe)  # type: ignore[arg-type]

        assert result == "Context with leading and trailing spaces."


class TestSingletonAndConvenienceFunction:
    """Tests for singleton and convenience function."""

    def test_get_context_generator_returns_same_instance(self) -> None:
        """Test that get_context_generator returns singleton."""
        # Reset singleton for test
        import services.context_generator as module
        from services.context_generator import get_context_generator

        module._context_generator = None

        with patch("services.context_generator.genai.Client"):
            gen1 = get_context_generator()
            gen2 = get_context_generator()

        assert gen1 is gen2

    @pytest.mark.asyncio
    async def test_generate_recipe_context_convenience_function(self) -> None:
        """Test the convenience function for generating context."""
        from services.context_generator import generate_recipe_context

        mock_response = MagicMock()
        mock_response.text = "Convenience function test result."

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("services.context_generator.genai.Client", return_value=mock_client):
            # Reset singleton
            import services.context_generator as module

            module._context_generator = None

            recipe = MockRecipe(name="Test")
            result = await generate_recipe_context(recipe)  # type: ignore[arg-type]

        assert result == "Convenience function test result."
