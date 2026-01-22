"""Tests for the embedding service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
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
    """Mock Recipe model for testing embedding generation."""

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


class TestGenerateRecipeText:
    """Tests for generate_recipe_text function."""

    def test_generate_text_with_all_fields(self) -> None:
        """Test text generation with all recipe fields."""
        from services.embedding_service import generate_recipe_text

        recipe = MockRecipe(
            name="Chicken Tikka Masala",
            description="A creamy, spiced curry dish",
            recipeingredients=[
                MockRecipeIngredient("chicken"),
                MockRecipeIngredient("tomatoes"),
                MockRecipeIngredient("cream"),
            ],
            instructions=["Marinate chicken", "Grill chicken", "Make sauce"],
            prep_time_minutes=30,
            cook_time_minutes=45,
            difficulty="medium",
            course_type="dinner",
            ethnicity="Indian",
        )

        result = generate_recipe_text(recipe)  # type: ignore[arg-type]

        assert "Recipe: Chicken Tikka Masala" in result
        assert "A creamy, spiced curry dish" in result
        assert "Cuisine: Indian" in result
        assert "Course: dinner" in result
        assert "Difficulty: medium" in result
        assert "Time: 30 min prep, 45 min cook" in result
        assert "chicken" in result
        assert "tomatoes" in result
        assert "Marinate chicken" in result

    def test_generate_text_with_minimal_fields(self) -> None:
        """Test text generation with only required name."""
        from services.embedding_service import generate_recipe_text

        recipe = MockRecipe(name="Simple Dish")

        result = generate_recipe_text(recipe)  # type: ignore[arg-type]

        assert "Recipe: Simple Dish" in result
        # Other fields should not appear
        assert "Cuisine:" not in result
        assert "Course:" not in result
        assert "Difficulty:" not in result
        assert "Time:" not in result

    def test_generate_text_with_ingredients_only(self) -> None:
        """Test text generation with ingredients."""
        from services.embedding_service import generate_recipe_text

        recipe = MockRecipe(
            name="Salad",
            recipeingredients=[
                MockRecipeIngredient("lettuce"),
                MockRecipeIngredient("tomato"),
                MockRecipeIngredient("cucumber"),
            ],
        )

        result = generate_recipe_text(recipe)  # type: ignore[arg-type]

        assert "Ingredients: lettuce, tomato, cucumber" in result

    def test_generate_text_with_only_cook_time(self) -> None:
        """Test text generation with only cook time (no prep)."""
        from services.embedding_service import generate_recipe_text

        recipe = MockRecipe(name="Quick Dish", cook_time_minutes=15)

        result = generate_recipe_text(recipe)  # type: ignore[arg-type]

        assert "Time: 15 min cook" in result


class TestGenerateEmbedding:
    """Tests for generate_embedding function."""

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self) -> None:
        """Test successful embedding generation."""
        from services.embedding_service import generate_embedding

        # Create mock embedding result (768 dimensions, unnormalized)
        raw_embedding = list(np.random.randn(768))

        mock_embedding = MagicMock()
        mock_embedding.values = raw_embedding

        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        with patch(
            "services.embedding_service.get_embedding_client", return_value=mock_client
        ):
            result = await generate_embedding("Test text for embedding")

        assert len(result) == 768
        # Verify normalization (vector magnitude should be ~1.0)
        magnitude = np.linalg.norm(result)
        assert abs(magnitude - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_generate_embedding_uses_document_task_type(self) -> None:
        """Test that document embedding uses RETRIEVAL_DOCUMENT task type."""
        from services.embedding_service import generate_embedding

        raw_embedding = list(np.random.randn(768))
        mock_embedding = MagicMock()
        mock_embedding.values = raw_embedding

        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        with patch(
            "services.embedding_service.get_embedding_client", return_value=mock_client
        ):
            await generate_embedding("Test text")

        # Verify the call used correct task type
        call_kwargs = mock_client.aio.models.embed_content.call_args
        assert call_kwargs is not None
        config = call_kwargs.kwargs.get("config")
        assert config is not None
        assert config.task_type == "RETRIEVAL_DOCUMENT"
        assert config.output_dimensionality == 768

    @pytest.mark.asyncio
    async def test_generate_embedding_raises_on_empty_result(self) -> None:
        """Test that empty embedding result raises ValueError."""
        from services.embedding_service import generate_embedding

        mock_result = MagicMock()
        mock_result.embeddings = []  # Empty

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        with (
            patch(
                "services.embedding_service.get_embedding_client",
                return_value=mock_client,
            ),
            pytest.raises(ValueError, match="No embeddings returned"),
        ):
            await generate_embedding("Test text")


class TestGenerateQueryEmbedding:
    """Tests for generate_query_embedding function."""

    @pytest.mark.asyncio
    async def test_generate_query_embedding_success(self) -> None:
        """Test successful query embedding generation."""
        from services.embedding_service import generate_query_embedding

        raw_embedding = list(np.random.randn(768))
        mock_embedding = MagicMock()
        mock_embedding.values = raw_embedding

        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        with patch(
            "services.embedding_service.get_embedding_client", return_value=mock_client
        ):
            result = await generate_query_embedding("Find pasta recipes")

        assert len(result) == 768
        magnitude = np.linalg.norm(result)
        assert abs(magnitude - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_generate_query_embedding_uses_query_task_type(self) -> None:
        """Test that query embedding uses RETRIEVAL_QUERY task type."""
        from services.embedding_service import generate_query_embedding

        raw_embedding = list(np.random.randn(768))
        mock_embedding = MagicMock()
        mock_embedding.values = raw_embedding

        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        with patch(
            "services.embedding_service.get_embedding_client", return_value=mock_client
        ):
            await generate_query_embedding("chicken recipes")

        call_kwargs = mock_client.aio.models.embed_content.call_args
        assert call_kwargs is not None
        config = call_kwargs.kwargs.get("config")
        assert config is not None
        assert config.task_type == "RETRIEVAL_QUERY"


class TestGenerateRecipeEmbedding:
    """Tests for generate_recipe_embedding function (full pipeline)."""

    @pytest.mark.asyncio
    async def test_generate_recipe_embedding_full_pipeline(self) -> None:
        """Test the full recipe embedding pipeline with context."""
        from services.embedding_service import generate_recipe_embedding

        raw_embedding = list(np.random.randn(768))
        mock_embedding = MagicMock()
        mock_embedding.values = raw_embedding

        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]

        mock_embed_client = MagicMock()
        mock_embed_client.aio = MagicMock()
        mock_embed_client.aio.models = MagicMock()
        mock_embed_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        recipe = MockRecipe(
            name="Beef Tacos",
            description="Authentic Mexican street tacos",
            ethnicity="Mexican",
        )

        with (
            patch(
                "services.embedding_service.generate_recipe_context",
                new_callable=AsyncMock,
                return_value="A spicy Mexican dish perfect for taco night.",
            ),
            patch(
                "services.embedding_service.get_embedding_client",
                return_value=mock_embed_client,
            ),
        ):
            context, embedding = await generate_recipe_embedding(recipe)  # type: ignore[arg-type]

        # Verify context was generated
        assert context == "A spicy Mexican dish perfect for taco night."

        # Verify embedding is normalized 768-dim vector
        assert len(embedding) == 768
        magnitude = np.linalg.norm(embedding)
        assert abs(magnitude - 1.0) < 1e-6

    @pytest.mark.asyncio
    async def test_generate_recipe_embedding_combines_context_and_text(self) -> None:
        """Test that embedding is generated from combined context + recipe text."""
        from services.embedding_service import generate_recipe_embedding

        raw_embedding = list(np.random.randn(768))
        mock_embedding = MagicMock()
        mock_embedding.values = raw_embedding

        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]

        mock_embed_client = MagicMock()
        mock_embed_client.aio = MagicMock()
        mock_embed_client.aio.models = MagicMock()
        mock_embed_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        recipe = MockRecipe(name="Test Recipe")

        with (
            patch(
                "services.embedding_service.generate_recipe_context",
                new_callable=AsyncMock,
                return_value="Context prefix.",
            ),
            patch(
                "services.embedding_service.get_embedding_client",
                return_value=mock_embed_client,
            ),
        ):
            await generate_recipe_embedding(recipe)  # type: ignore[arg-type]

        # Check that embed_content was called with combined text
        call_args = mock_embed_client.aio.models.embed_content.call_args
        contents = call_args.kwargs.get("contents", "")
        assert "Context prefix." in contents
        assert "Recipe: Test Recipe" in contents


class TestEmbeddingNormalization:
    """Tests for embedding normalization."""

    @pytest.mark.asyncio
    async def test_embedding_normalization_preserves_direction(self) -> None:
        """Test that normalization preserves vector direction."""
        from services.embedding_service import generate_embedding

        # Create a simple known vector
        known_direction = np.array([1.0, 2.0, 3.0] + [0.0] * 765)
        scaled_vector = list(known_direction * 100)  # Scale up

        mock_embedding = MagicMock()
        mock_embedding.values = scaled_vector

        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]

        mock_client = MagicMock()
        mock_client.aio = MagicMock()
        mock_client.aio.models = MagicMock()
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        with patch(
            "services.embedding_service.get_embedding_client", return_value=mock_client
        ):
            result = await generate_embedding("Test")

        # First three elements should have same ratio
        normalized = np.array(result)
        assert normalized[0] != 0
        ratio_1_to_0 = normalized[1] / normalized[0]
        expected_ratio = 2.0 / 1.0
        assert abs(ratio_1_to_0 - expected_ratio) < 1e-6
