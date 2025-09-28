"""AI agents and services for recipe extraction."""

import logging
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, ModelSettings

from schemas.ai import AIGeneratedRecipe
from schemas.recipes import (
    IngredientIn,
    IngredientPrepIn,
    RecipeCategory,
    RecipeCreate,
    RecipeDifficulty,
)


logger = logging.getLogger(__name__)


class RecipeExtractionResult(BaseModel):
    """Result from AI recipe extraction."""
    
    title: str
    description: str | None = None
    ingredients: list[dict[str, Any]]
    instructions: list[str]
    prep_time_minutes: int
    cook_time_minutes: int
    serving_min: int
    serving_max: int | None = None
    difficulty: str = "medium"
    category: str = "dinner"
    ethnicity: str | None = None
    oven_temperature_f: int | None = None
    user_notes: str | None = None
    confidence_score: float = 0.8


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


def create_recipe_agent():  # type: ignore
    """Create a pydantic-ai agent for recipe extraction."""
    # Use Gemini Flash for fast, cost-effective extraction
    # Note: pydantic-ai will handle model configuration internally
    return Agent(
        "gemini-1.5-flash",  # Use fast model for cost efficiency
        system_prompt=RECIPE_EXTRACTION_PROMPT,
        result_type=RecipeExtractionResult,
    )


def convert_to_recipe_create(
    extraction_result: RecipeExtractionResult, 
    source_url: str
) -> AIGeneratedRecipe:
    """Convert extraction result to RecipeCreate schema with validation."""
    
    # Convert ingredients to proper schema
    ingredients: list[IngredientIn] = []
    for ing_data in extraction_result.ingredients:
        prep = None
        if ing_data.get("prep_method") or ing_data.get("prep_size"):
            prep = IngredientPrepIn(
                method=ing_data.get("prep_method"),
                size_descriptor=ing_data.get("prep_size")
            )
        
        ingredient = IngredientIn(
            name=ing_data["name"],
            quantity_value=ing_data.get("quantity_value"),
            quantity_unit=ing_data.get("quantity_unit"),
            prep=prep,
            is_optional=ing_data.get("is_optional", False)
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
        source_url=source_url
    )