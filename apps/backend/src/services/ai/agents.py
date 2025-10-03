"""AI agents and services for recipe extraction."""

import logging
from collections.abc import Mapping
from typing import Any

from pydantic_ai import Agent

from schemas.ai import AIGeneratedRecipe, ExtractionNotFound, RecipeExtractionResult
from schemas.recipes import (
    IngredientIn,
    IngredientPrepIn,
    RecipeCategory,
    RecipeCreate,
    RecipeDifficulty,
)


logger = logging.getLogger(__name__)


# System prompt for recipe extraction
RECIPE_EXTRACTION_PROMPT = """
You are a skilled recipe extraction AI. Extract structured recipe information
from the provided HTML content.

Your task is to identify and extract:
1. Recipe title (required)
2. Description/summary (optional)
3. Ingredients list with quantities and units (required)
4. Step-by-step instructions (required)
5. Preparation and cooking times in minutes (required)
6. Number of servings (required)
7. Difficulty level: easy, medium, or hard (default: medium)
8. Category: breakfast, lunch, dinner, dessert, snack, or appetizer (default: dinner)
9. Cuisine/ethnicity (optional)
10. Oven temperature in Fahrenheit (optional)
11. Any special notes (optional)

For ingredients, extract:
- name (required)
- quantity_value (numeric value, optional)
- quantity_unit (unit like "cup", "tsp", "lb", optional)
- preparation method and size if mentioned (like "chopped", "diced", optional)
- whether ingredient is optional (default: false)

Return a confidence score (0.0-1.0) indicating how confident you are in the
extraction quality.

Be conservative with time estimates and serving sizes. If unclear, make
reasonable assumptions. Focus on extracting clean, readable text without HTML
artifacts or advertisements.
"""


def create_recipe_agent() -> Agent:
    """Create a pydantic-ai agent for recipe extraction."""
    # Use Gemini Flash for fast, cost-effective extraction
    # Note: pydantic-ai will handle model configuration internally
    # Register both the normal extraction result and a simple failure model
    # as possible output types. This maps to Pydantic AI's tool-output pattern
    # where the model can explicitly choose the failure output when no recipe
    # is found on the page.
    return Agent(
        "gemini-2.5-flash",
        system_prompt=RECIPE_EXTRACTION_PROMPT,
        output_type=[RecipeExtractionResult, ExtractionNotFound],
    )


def convert_to_recipe_create(
    extraction_result: RecipeExtractionResult, source_url: str
) -> AIGeneratedRecipe:
    """Convert extraction result to RecipeCreate schema with validation."""

    # Convert ingredients to proper schema. The agent may return ingredients
    # as plain mappings (dict) or as Pydantic models. Handle both cases.
    ingredients: list[IngredientIn] = []

    def _val(obj: object, key: str) -> Any:
        if isinstance(obj, Mapping):
            return obj.get(key)
        return getattr(obj, key, None)

    for ing_data in extraction_result.ingredients:
        prep_method = _val(ing_data, "prep_method")
        prep_size = _val(ing_data, "prep_size")

        prep: IngredientPrepIn | None = None
        if prep_method or prep_size:
            prep = IngredientPrepIn(
                method=prep_method,
                size_descriptor=prep_size,
            )

        name = _val(ing_data, "name")
        if name is None:
            raise ValueError("Ingredient entry missing required 'name' field")

        ingredient = IngredientIn(
            name=name,
            quantity_value=_val(ing_data, "quantity_value"),
            quantity_unit=_val(ing_data, "quantity_unit"),
            prep=prep,
            is_optional=_val(ing_data, "is_optional") or False,
        )
        ingredients.append(ingredient)

    # Validate and convert enums
    try:
        difficulty = RecipeDifficulty(extraction_result.difficulty.lower())
    except ValueError:
        difficulty = RecipeDifficulty.MEDIUM

    try:
        category = RecipeCategory(extraction_result.category.lower())
    except ValueError:
        category = RecipeCategory.DINNER

    # Create the recipe data
    recipe_data = RecipeCreate(
        title=extraction_result.title,
        description=extraction_result.description,
        prep_time_minutes=extraction_result.prep_time_minutes,
        cook_time_minutes=extraction_result.cook_time_minutes,
        serving_min=extraction_result.serving_min,
        serving_max=extraction_result.serving_max,
        instructions=extraction_result.instructions,
        difficulty=difficulty,
        category=category,
        ethnicity=extraction_result.ethnicity,
        oven_temperature_f=extraction_result.oven_temperature_f,
        user_notes=extraction_result.user_notes,
        link_source=source_url,  # Store original URL
        ingredients=ingredients,
    )

    return AIGeneratedRecipe(
        recipe_data=recipe_data,
        confidence_score=extraction_result.confidence_score,
        extraction_notes=None,
        source_url=source_url,
    )
