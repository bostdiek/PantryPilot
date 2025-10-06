"""Schema model validation tests for AI request/response objects."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas.ai import AIGeneratedRecipe, AIRecipeFromUrlRequest
from schemas.recipes import IngredientIn, RecipeCategory, RecipeCreate, RecipeDifficulty


def test_ai_recipe_from_url_request_validation():
    valid = AIRecipeFromUrlRequest(
        source_url="https://example.com/recipe", prompt_override="Custom"
    )
    assert str(valid.source_url) == "https://example.com/recipe"
    assert valid.prompt_override == "Custom"
    minimal = AIRecipeFromUrlRequest(source_url="https://example.com/recipe")
    assert minimal.prompt_override is None
    with pytest.raises(ValidationError):
        AIRecipeFromUrlRequest(source_url="not-a-url")


def test_ai_generated_recipe_schema():
    recipe_data = RecipeCreate(
        title="Test Recipe",
        prep_time_minutes=10,
        cook_time_minutes=20,
        serving_min=2,
        instructions=["Step 1", "Step 2"],
        difficulty=RecipeDifficulty.EASY,
        category=RecipeCategory.LUNCH,
        ingredients=[
            IngredientIn(
                name="Test Ingredient", quantity_value=1.0, quantity_unit="cup"
            )
        ],
    )
    ai_recipe = AIGeneratedRecipe(
        recipe_data=recipe_data,
        confidence_score=0.9,
        source_url="https://example.com/recipe",
        extraction_notes="Good extraction",
    )
    assert ai_recipe.confidence_score == 0.9
    assert ai_recipe.recipe_data.title == "Test Recipe"
    assert len(ai_recipe.recipe_data.ingredients) == 1
