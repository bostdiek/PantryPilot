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

        with patch("google.genai.Client", return_value=mock_client):
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

        with patch("google.genai.Client", return_value=mock_client):
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

        with patch("google.genai.Client", return_value=mock_client):
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

        with patch("google.genai.Client", return_value=mock_client):
            generator = RecipeContextGenerator(api_key="test-key")
            recipe = MockRecipe(name="Test")

            result = await generator.generate_context(recipe)  # type: ignore[arg-type]

        assert result == "Context with leading and trailing spaces."


class TestAzureProviderSupport:
    """Tests for Azure OpenAI provider support."""

    @pytest.mark.asyncio
    async def test_uses_azure_when_configured(self) -> None:
        """Test uses Azure OpenAI when LLM_PROVIDER is azure_openai."""
        from services.context_generator import RecipeContextGenerator

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "This is an Italian dinner recipe."
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with (
            patch("services.context_generator._is_azure_provider", return_value=True),
            patch("services.context_generator.get_settings") as mock_settings,
            patch("openai.AsyncAzureOpenAI", return_value=mock_client),
        ):
            mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
                "https://test.openai.azure.com"
            )
            mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.return_value.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            mock_settings.return_value.TEXT_MODEL = "gpt-35-turbo"

            generator = RecipeContextGenerator()
            recipe = MockRecipe(name="Pasta", ethnicity="Italian", course_type="dinner")

            result = await generator.generate_context(recipe)  # type: ignore[arg-type]

            assert result == "This is an Italian dinner recipe."
            mock_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_azure_reasoning_model_uses_max_completion_tokens(self) -> None:
        """Test Azure reasoning models use max_completion_tokens without temperature."""
        from services.context_generator import RecipeContextGenerator

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "This is a reasoning model response."
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with (
            patch("services.context_generator._is_azure_provider", return_value=True),
            patch("services.context_generator.get_settings") as mock_settings,
            patch("openai.AsyncAzureOpenAI", return_value=mock_client),
        ):
            mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
                "https://test.openai.azure.com"
            )
            mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.return_value.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            mock_settings.return_value.TEXT_MODEL = "gpt-5-mini"

            generator = RecipeContextGenerator()
            recipe = MockRecipe(name="Test", ethnicity="Italian", course_type="dinner")

            result = await generator.generate_context(recipe)  # type: ignore[arg-type]

            assert result == "This is a reasoning model response."

            # Verify the call was made with max_completion_tokens, not max_tokens
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert "max_completion_tokens" in call_kwargs
            assert "max_tokens" not in call_kwargs
            assert "temperature" not in call_kwargs

    @pytest.mark.asyncio
    async def test_azure_standard_model_uses_max_tokens_and_temperature(self) -> None:
        """Test Azure standard models use max_tokens and temperature."""
        from services.context_generator import RecipeContextGenerator

        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "This is a standard model response."
        mock_response.choices = [mock_choice]

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with (
            patch("services.context_generator._is_azure_provider", return_value=True),
            patch("services.context_generator.get_settings") as mock_settings,
            patch("openai.AsyncAzureOpenAI", return_value=mock_client),
        ):
            mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
                "https://test.openai.azure.com"
            )
            mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.return_value.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            mock_settings.return_value.TEXT_MODEL = "gpt-35-turbo"

            generator = RecipeContextGenerator()
            recipe = MockRecipe(name="Test", ethnicity="Mexican", course_type="dinner")

            result = await generator.generate_context(recipe)  # type: ignore[arg-type]

            assert result == "This is a standard model response."

            # Verify the call was made with max_tokens and temperature, not
            # max_completion_tokens
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert "max_tokens" in call_kwargs
            assert "temperature" in call_kwargs
            assert call_kwargs["temperature"] == 0.3
            assert "max_completion_tokens" not in call_kwargs

    @pytest.mark.asyncio
    async def test_azure_returns_none_on_empty_response(self) -> None:
        """Test Azure path returns None when response is empty."""
        from services.context_generator import RecipeContextGenerator

        mock_response = MagicMock()
        mock_response.choices = []

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with (
            patch("services.context_generator._is_azure_provider", return_value=True),
            patch("services.context_generator.get_settings") as mock_settings,
            patch("openai.AsyncAzureOpenAI", return_value=mock_client),
        ):
            mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
                "https://test.openai.azure.com"
            )
            mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.return_value.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            mock_settings.return_value.TEXT_MODEL = "gpt-35-turbo"

            generator = RecipeContextGenerator()
            recipe = MockRecipe(name="Fallback Recipe", ethnicity="Mexican")

            result = await generator.generate_context(recipe)  # type: ignore[arg-type]

            # Should fall back to metadata-based context
            assert "Mexican recipe" in result
            assert "Fallback Recipe" in result

    @pytest.mark.asyncio
    async def test_azure_fallback_on_exception(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test falls back when Azure raises exception."""
        from services.context_generator import RecipeContextGenerator

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("Azure API error")
        )

        with (
            patch("services.context_generator._is_azure_provider", return_value=True),
            patch("services.context_generator.get_settings") as mock_settings,
            patch("openai.AsyncAzureOpenAI", return_value=mock_client),
        ):
            mock_settings.return_value.AZURE_OPENAI_ENDPOINT = (
                "https://test.openai.azure.com"
            )
            mock_settings.return_value.AZURE_OPENAI_API_KEY = "test-key"
            mock_settings.return_value.AZURE_OPENAI_API_VERSION = "2024-02-15-preview"
            mock_settings.return_value.TEXT_MODEL = "gpt-35-turbo"

            generator = RecipeContextGenerator()
            recipe = MockRecipe(name="Error Recipe", course_type="dinner")

            result = await generator.generate_context(recipe)  # type: ignore[arg-type]

            # Should use fallback
            assert "dinner" in result
            assert "Error Recipe" in result
            assert "Failed to generate context" in caplog.text


class TestSingletonAndConvenienceFunction:
    """Tests for singleton and convenience function."""

    def test_get_context_generator_returns_same_instance(self) -> None:
        """Test that get_context_generator returns singleton."""
        # Reset singleton for test
        import services.context_generator as module
        from services.context_generator import get_context_generator

        module._context_generator = None

        with patch("google.genai.Client"):
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

        with patch("google.genai.Client", return_value=mock_client):
            # Reset singleton
            import services.context_generator as module

            module._context_generator = None

            recipe = MockRecipe(name="Test")
            result = await generate_recipe_context(recipe)  # type: ignore[arg-type]

        assert result == "Convenience function test result."


class TestIsReasoningModel:
    """Tests for _is_reasoning_model helper function."""

    def test_recognizes_known_reasoning_models(self) -> None:
        """Test that known reasoning models from REASONING_MODELS set are recognized."""
        from services.context_generator import _is_reasoning_model

        # Test all models in the REASONING_MODELS set
        assert _is_reasoning_model("gpt-5-mini") is True
        assert _is_reasoning_model("gpt-5-nano") is True
        assert _is_reasoning_model("o1-mini") is True
        assert _is_reasoning_model("o1-preview") is True
        assert _is_reasoning_model("o1") is True
        assert _is_reasoning_model("o3-mini") is True

    def test_recognizes_reasoning_model_prefixes(self) -> None:
        """Test that models with reasoning prefixes are recognized."""
        from services.context_generator import _is_reasoning_model

        # Test gpt-5-* prefix variations
        assert _is_reasoning_model("gpt-5-turbo") is True
        assert _is_reasoning_model("gpt-5-large") is True
        assert _is_reasoning_model("gpt-5-custom-deployment") is True

        # Test o1-* prefix variations
        assert _is_reasoning_model("o1-custom") is True
        assert _is_reasoning_model("o1-deployment-name") is True

        # Test o3-* prefix variations
        assert _is_reasoning_model("o3-preview") is True
        assert _is_reasoning_model("o3-custom") is True
        assert _is_reasoning_model("o3") is True

    def test_rejects_non_reasoning_models(self) -> None:
        """Test that standard models are not recognized as reasoning models."""
        from services.context_generator import _is_reasoning_model

        # Standard GPT models
        assert _is_reasoning_model("gpt-35-turbo") is False
        assert _is_reasoning_model("gpt-4") is False
        assert _is_reasoning_model("gpt-4-turbo") is False
        assert _is_reasoning_model("gpt-4o") is False
        assert _is_reasoning_model("gpt-4o-mini") is False

        # Other models
        assert _is_reasoning_model("text-embedding-ada-002") is False
        assert _is_reasoning_model("gemini-flash") is False
        assert _is_reasoning_model("custom-model") is False

    def test_handles_deployment_names_with_suffixes(self) -> None:
        """Test that deployment names with suffixes are handled correctly."""
        from services.context_generator import _is_reasoning_model

        # Reasoning models with custom deployment suffixes
        assert _is_reasoning_model("gpt-5-mini-prod") is True
        assert _is_reasoning_model("o1-mini-v2") is True
        assert _is_reasoning_model("o3-mini-test") is True

        # Non-reasoning models with similar patterns should not match
        assert _is_reasoning_model("my-gpt-5-model") is False
        assert _is_reasoning_model("custom-o1") is False
