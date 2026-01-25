"""Tests for the deduplication service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic_ai import models


# Block any real model requests in tests
models.ALLOW_MODEL_REQUESTS = False


# ============================================================================
# TEST CLASSES
# ============================================================================


class TestGenerateIngredientHash:
    """Tests for generate_ingredient_hash function."""

    def test_generate_hash_basic(self) -> None:
        """Test basic hash generation."""
        from services.deduplication_service import generate_ingredient_hash

        ingredients = ["flour", "sugar", "eggs"]
        result = generate_ingredient_hash(ingredients)

        assert isinstance(result, str)
        assert len(result) == 16  # Truncated to 16 chars

    def test_generate_hash_normalizes_case(self) -> None:
        """Test that hash is case-insensitive."""
        from services.deduplication_service import generate_ingredient_hash

        hash1 = generate_ingredient_hash(["Flour", "SUGAR", "Eggs"])
        hash2 = generate_ingredient_hash(["flour", "sugar", "eggs"])

        assert hash1 == hash2

    def test_generate_hash_normalizes_whitespace(self) -> None:
        """Test that hash strips whitespace."""
        from services.deduplication_service import generate_ingredient_hash

        hash1 = generate_ingredient_hash(["  flour  ", "sugar", "eggs"])
        hash2 = generate_ingredient_hash(["flour", "sugar", "eggs"])

        assert hash1 == hash2

    def test_generate_hash_sorts_ingredients(self) -> None:
        """Test that hash is order-independent."""
        from services.deduplication_service import generate_ingredient_hash

        hash1 = generate_ingredient_hash(["flour", "sugar", "eggs"])
        hash2 = generate_ingredient_hash(["eggs", "flour", "sugar"])

        assert hash1 == hash2

    def test_generate_hash_different_for_different_ingredients(self) -> None:
        """Test that different ingredients produce different hashes."""
        from services.deduplication_service import generate_ingredient_hash

        hash1 = generate_ingredient_hash(["flour", "sugar", "eggs"])
        hash2 = generate_ingredient_hash(["butter", "milk", "salt"])

        assert hash1 != hash2

    def test_generate_hash_empty_list(self) -> None:
        """Test hash generation with empty list."""
        from services.deduplication_service import generate_ingredient_hash

        result = generate_ingredient_hash([])

        # Should still return a valid hash of empty string
        assert isinstance(result, str)
        assert len(result) == 16


class TestCheckRecipeDuplicate:
    """Tests for check_recipe_duplicate function."""

    @pytest.mark.asyncio
    async def test_no_duplicate_found(self) -> None:
        """Test when no duplicate exists."""
        from services.deduplication_service import check_recipe_duplicate

        mock_db = AsyncMock()
        user_id = uuid4()

        # Mock exact match query - no results
        mock_exact_result = MagicMock()
        mock_exact_result.scalars.return_value.first.return_value = None

        # Mock fuzzy match query - no results
        mock_fuzzy_result = MagicMock()
        mock_fuzzy_result.mappings.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_exact_result, mock_fuzzy_result]

        result = await check_recipe_duplicate(
            db=mock_db,
            user_id=user_id,
            name="Unique Recipe Name",
        )

        assert result["is_duplicate"] is False
        assert result["exact_match"] is None
        assert result["similar_matches"] == []
        assert result["reason"] is None

    @pytest.mark.asyncio
    async def test_exact_match_found(self) -> None:
        """Test when exact name match exists."""
        from services.deduplication_service import check_recipe_duplicate

        mock_db = AsyncMock()
        user_id = uuid4()

        # Create mock existing recipe
        mock_recipe = MagicMock()
        mock_recipe.name = "Spaghetti Carbonara"

        # Mock exact match query - found
        mock_exact_result = MagicMock()
        mock_exact_result.scalars.return_value.first.return_value = mock_recipe

        mock_db.execute.return_value = mock_exact_result

        result = await check_recipe_duplicate(
            db=mock_db,
            user_id=user_id,
            name="Spaghetti Carbonara",
        )

        assert result["is_duplicate"] is True
        assert result["exact_match"] == mock_recipe
        assert "Exact name match" in result["reason"]

    @pytest.mark.asyncio
    async def test_similar_match_found_below_threshold(self) -> None:
        """Test when similar (but not duplicate) match exists."""
        from services.deduplication_service import check_recipe_duplicate

        mock_db = AsyncMock()
        user_id = uuid4()

        # Mock exact match query - no results
        mock_exact_result = MagicMock()
        mock_exact_result.scalars.return_value.first.return_value = None

        # Mock fuzzy match query - similar but not duplicate
        recipe_id = uuid4()
        mock_fuzzy_result = MagicMock()
        mock_fuzzy_result.mappings.return_value.all.return_value = [
            {"id": recipe_id, "name": "Spaghetti Bolognese", "sim": 0.75}
        ]

        mock_db.execute.side_effect = [mock_exact_result, mock_fuzzy_result]

        result = await check_recipe_duplicate(
            db=mock_db,
            user_id=user_id,
            name="Spaghetti Carbonara",
        )

        # Not a duplicate (sim < 0.95) but has similar matches
        assert result["is_duplicate"] is False
        assert len(result["similar_matches"]) == 1
        assert result["similar_matches"][0]["name"] == "Spaghetti Bolognese"
        assert result["similar_matches"][0]["similarity"] == 0.75

    @pytest.mark.asyncio
    async def test_very_similar_match_is_duplicate(self) -> None:
        """Test when very similar match (>95%) is found."""
        from services.deduplication_service import check_recipe_duplicate

        mock_db = AsyncMock()
        user_id = uuid4()

        # Mock exact match query - no results
        mock_exact_result = MagicMock()
        mock_exact_result.scalars.return_value.first.return_value = None

        # Mock fuzzy match query - very similar (>0.95)
        recipe_id = uuid4()
        mock_fuzzy_result = MagicMock()
        mock_fuzzy_result.mappings.return_value.all.return_value = [
            {"id": recipe_id, "name": "Spaghetti Carbonara!", "sim": 0.97}
        ]

        mock_db.execute.side_effect = [mock_exact_result, mock_fuzzy_result]

        result = await check_recipe_duplicate(
            db=mock_db,
            user_id=user_id,
            name="Spaghetti Carbonara",
        )

        assert result["is_duplicate"] is True
        assert "Very similar name" in result["reason"]
        assert "97%" in result["reason"]


class TestCheckIngredientDuplicate:
    """Tests for check_ingredient_duplicate function."""

    @pytest.mark.asyncio
    async def test_no_ingredient_duplicate(self) -> None:
        """Test when no ingredient duplicate exists."""
        from services.deduplication_service import check_ingredient_duplicate

        mock_db = AsyncMock()
        user_id = uuid4()

        # Mock exact match - no results
        mock_exact_result = MagicMock()
        mock_exact_result.scalars.return_value.first.return_value = None

        # Mock fuzzy match - no results
        mock_fuzzy_result = MagicMock()
        mock_fuzzy_result.mappings.return_value.all.return_value = []

        mock_db.execute.side_effect = [mock_exact_result, mock_fuzzy_result]

        result = await check_ingredient_duplicate(
            db=mock_db,
            user_id=user_id,
            ingredient_name="unique ingredient",
        )

        assert result["is_duplicate"] is False
        assert result["exact_match"] is None

    @pytest.mark.asyncio
    async def test_exact_ingredient_match(self) -> None:
        """Test when exact ingredient match exists."""
        from services.deduplication_service import check_ingredient_duplicate

        mock_db = AsyncMock()
        user_id = uuid4()

        mock_ingredient = MagicMock()
        mock_ingredient.ingredient_name = "flour"

        mock_exact_result = MagicMock()
        mock_exact_result.scalars.return_value.first.return_value = mock_ingredient

        mock_db.execute.return_value = mock_exact_result

        result = await check_ingredient_duplicate(
            db=mock_db,
            user_id=user_id,
            ingredient_name="flour",
        )

        assert result["is_duplicate"] is True
        assert result["exact_match"] == mock_ingredient


class TestFindDuplicateRecipes:
    """Tests for find_duplicate_recipes function."""

    @pytest.mark.asyncio
    async def test_find_duplicates_returns_pairs(self) -> None:
        """Test finding duplicate recipe pairs."""
        from services.deduplication_service import find_duplicate_recipes

        mock_db = AsyncMock()

        # Mock result with duplicate pairs
        id1, id2 = uuid4(), uuid4()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [
            {
                "id1": id1,
                "name1": "Chicken Tikka",
                "user_id1": uuid4(),
                "id2": id2,
                "name2": "Chicken Tikka Masala",
                "user_id2": uuid4(),
                "sim": 0.88,
            }
        ]

        mock_db.execute.return_value = mock_result

        result = await find_duplicate_recipes(db=mock_db)

        assert len(result) == 1
        assert result[0]["recipe_1"]["name"] == "Chicken Tikka"
        assert result[0]["recipe_2"]["name"] == "Chicken Tikka Masala"
        assert result[0]["similarity"] == 0.88

    @pytest.mark.asyncio
    async def test_find_duplicates_with_user_filter(self) -> None:
        """Test finding duplicates for specific user."""
        from services.deduplication_service import find_duplicate_recipes

        mock_db = AsyncMock()
        user_id = uuid4()

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []

        mock_db.execute.return_value = mock_result

        await find_duplicate_recipes(db=mock_db, user_id=user_id)

        # Verify execute was called
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_find_duplicates_custom_threshold(self) -> None:
        """Test finding duplicates with custom threshold."""
        from services.deduplication_service import find_duplicate_recipes

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []

        mock_db.execute.return_value = mock_result

        await find_duplicate_recipes(db=mock_db, similarity_threshold=0.9)

        # Verify execute was called with custom threshold
        call_args = mock_db.execute.call_args
        assert call_args is not None
        params = call_args[0][1]  # Second positional arg is params dict
        assert params["threshold"] == 0.9

    @pytest.mark.asyncio
    async def test_find_duplicates_empty_result(self) -> None:
        """Test when no duplicates found."""
        from services.deduplication_service import find_duplicate_recipes

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []

        mock_db.execute.return_value = mock_result

        result = await find_duplicate_recipes(db=mock_db)

        assert result == []


class TestSimilarityThresholds:
    """Tests for similarity threshold constants."""

    def test_recipe_threshold_value(self) -> None:
        """Test recipe similarity threshold is reasonable."""
        from services.deduplication_service import RECIPE_SIMILARITY_THRESHOLD

        # Should be between 0.3 and 0.9
        assert 0.3 <= RECIPE_SIMILARITY_THRESHOLD <= 0.9

    def test_ingredient_threshold_value(self) -> None:
        """Test ingredient similarity threshold is reasonable."""
        from services.deduplication_service import INGREDIENT_SIMILARITY_THRESHOLD

        # Should be higher than recipe threshold
        assert 0.5 <= INGREDIENT_SIMILARITY_THRESHOLD <= 0.95
