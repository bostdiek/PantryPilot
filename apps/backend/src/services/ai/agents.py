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


# System prompt for recipe extraction (explicit about separating prep descriptors)
RECIPE_EXTRACTION_PROMPT = """
You are a skilled recipe extraction AI. Extract structured recipe information
from the provided HTML content.

Your task is to identify and extract:
1. title (required)
2. description (optional)
3. ingredients list (required)
4. instructions (required list of steps)
5. prep_time_minutes and cook_time_minutes (required; integers minutes)
6. serving_min (required) and serving_max (optional, >= serving_min)
7. difficulty: easy | medium | hard (default medium)
8. category: breakfast | lunch | dinner | dessert | snack | appetizer (default dinner)
9. ethnicity (optional)
10. oven_temperature_f (optional integer <= 550)
11. user_notes (optional)

INGREDIENT RULES:
- Each ingredient object MUST include:
    name;
    optional quantity_value (number);
    optional quantity_unit (string);
    optional prep (object);
    is_optional (boolean, default false).
- prep object fields:
        - method: main preparation verb ("sliced", "chopped", "diced",
            "minced", "grated", "shredded", "peeled", etc.)
        - size_descriptor: adverb or size/cut descriptor ("finely", "coarsely",
            "thinly", "large", "small", etc.)
- Do NOT leave preparation words inside the name. Split them out. Examples:
    * "sliced black olives" -> name: "black olives", prep.method: "sliced"
        * "finely chopped fresh parsley" -> name: "fresh parsley",
            prep.method: "chopped", prep.size_descriptor: "finely"
        * "coarsely shredded cheddar cheese" -> name: "cheddar cheese",
            prep.method: "shredded", prep.size_descriptor: "coarsely"
- If multiple adverbs: keep the most relevant single size descriptor
    ("very finely chopped" -> size_descriptor: "finely").
- quantity_unit should not repeat inside name. Use canonical units like cup,
    tsp, tbsp, pound, ounce, can, gram, kilogram.
- Only include a unit when clearly specified.

Always separate prep words even if uncertain; prefer prep.method over embedding.

Return confidence_score (0.0-1.0). Provide clean text only (no HTML, ads, scripts).
"""


def create_recipe_agent() -> Agent:
    """Create a pydantic-ai agent for recipe extraction."""
    # Use Gemini Flash for fast, cost-effective extraction
    # Note: pydantic-ai will handle model configuration internally
    # Register both the normal extraction result and a simple failure model
    # as possible output types. This maps to Pydantic AI's tool-output pattern
    # where the model can explicitly choose the failure output when no recipe
    # is found on the page.
    # Register both the normal extraction result and two explicit
    # failure models (legacy ExtractionNotFound plus NoFoodOrDrinkRecipe)
    # so the agent can choose a clear failure tool if it detects non-food
    # documentation pages.
    from schemas.ai import NoFoodOrDrinkRecipe

    return Agent(
        "gemini-2.5-flash-lite",
        system_prompt=RECIPE_EXTRACTION_PROMPT,
        output_type=[RecipeExtractionResult, ExtractionNotFound, NoFoodOrDrinkRecipe],
    )


# Note: We intentionally accept AI-provided ingredient names and prep as-is.
# The previous normalization helper was removed so the agent's output is used
# verbatim.


def convert_to_recipe_create(
    extraction_result: RecipeExtractionResult, source_url: str
) -> AIGeneratedRecipe:
    """Convert extraction result to RecipeCreate schema with validation.

    Uses the AI-provided ingredient names and prep values verbatim.
    """

    ingredients: list[IngredientIn] = []

    def _val(obj: object, key: str) -> Any:
        if isinstance(obj, Mapping):
            return obj.get(key)
        return getattr(obj, key, None)

    for ing_data in extraction_result.ingredients:
        name = _val(ing_data, "name")
        if name is None:
            raise ValueError("Ingredient entry missing required 'name' field")

        # Support flat prep_method/prep_size and nested prep {method, size_descriptor}
        prep_method = _val(ing_data, "prep_method")
        prep_size = _val(ing_data, "prep_size")
        nested_prep = _val(ing_data, "prep")
        if nested_prep and isinstance(nested_prep, Mapping):
            prep_method = prep_method or nested_prep.get("method")
            prep_size = prep_size or nested_prep.get("size_descriptor")

        prep: IngredientPrepIn | None = None
        if prep_method or prep_size:
            prep = IngredientPrepIn(method=prep_method, size_descriptor=prep_size)

        ingredient = IngredientIn(
            name=name,
            quantity_value=_val(ing_data, "quantity_value"),
            quantity_unit=_val(ing_data, "quantity_unit"),
            prep=prep,
            is_optional=bool(_val(ing_data, "is_optional") or False),
        )
        ingredients.append(ingredient)

    try:
        difficulty = RecipeDifficulty(extraction_result.difficulty.lower())
    except Exception:  # noqa: BLE001
        difficulty = RecipeDifficulty.MEDIUM

    try:
        category = RecipeCategory(extraction_result.category.lower())
    except Exception:  # noqa: BLE001
        category = RecipeCategory.DINNER

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
        link_source=source_url,
        ingredients=ingredients,
    )

    return AIGeneratedRecipe(
        recipe_data=recipe_data,
        confidence_score=extraction_result.confidence_score,
        extraction_notes=None,
        source_url=source_url,
    )
