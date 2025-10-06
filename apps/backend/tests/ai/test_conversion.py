"""Tests for conversion logic convert_to_recipe_create."""

from __future__ import annotations

from schemas.ai import AIGeneratedRecipe
from schemas.recipes import RecipeCategory, RecipeDifficulty
from services.ai.agents import convert_to_recipe_create


def test_convert_to_recipe_create_basic(complex_recipe_extraction):
    result = convert_to_recipe_create(
        complex_recipe_extraction, "https://example.com/recipe"
    )
    assert isinstance(result, AIGeneratedRecipe)
    assert result.source_url == "https://example.com/recipe"
    assert result.recipe_data.title == "Coq au Vin"
    assert result.recipe_data.difficulty == RecipeDifficulty.HARD
    assert result.recipe_data.category == RecipeCategory.DINNER
    assert len(result.recipe_data.ingredients) == 10
