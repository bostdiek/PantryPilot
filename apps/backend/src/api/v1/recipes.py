"""Recipes API endpoints for the PantryPilot application.

This module defines all recipe-related API endpoints, including CRUD operations
for recipes and their ingredients.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.db import get_db
from src.models.ingredient_names import Ingredient
from src.models.recipe_ingredients import RecipeIngredient
from src.models.recipes_names import Recipe
from src.schemas.recipes import RecipeCategory, RecipeCreate, RecipeOut


router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.post(
    "/",
    response_model=RecipeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new recipe",
    description=(
        "Create a new recipe with its ingredients, "
        "returning the created recipe with IDs."
    ),
)
async def create_recipe(
    recipe_data: RecipeCreate, db: Annotated[AsyncSession, Depends(get_db)]
) -> RecipeOut:
    """Create a new recipe with ingredients.

    This endpoint creates a new recipe along with its associated ingredients,
    handling both new and existing ingredients appropriately.

    Args:
        recipe_data: The recipe data from the request body.
        db: The database session dependency.

    Returns:
        The newly created recipe with all its data.

    Raises:
        HTTPException: If there's an integrity error or other database issue.
    """
    try:
        # Create the recipe first
        total_time = recipe_data.prep_time_minutes + recipe_data.cook_time_minutes
        now_ts = datetime.now(UTC)
        new_recipe = Recipe(
            id=uuid.uuid4(),
            name=recipe_data.title,
            prep_time_minutes=recipe_data.prep_time_minutes,
            cook_time_minutes=recipe_data.cook_time_minutes,
            total_time_minutes=total_time,
            serving_min=recipe_data.serving_min,
            serving_max=recipe_data.serving_max,
            ethnicity=recipe_data.ethnicity,
            # Map category to course_type
            course_type=recipe_data.category.value,
            instructions=recipe_data.instructions,
            user_notes=recipe_data.user_notes,
            link_source=recipe_data.link_source,
            # Fallback timestamps for tests/mocks without DB defaults
            created_at=now_ts,
            updated_at=now_ts,
        )

        db.add(new_recipe)
        await db.flush()  # Flush to get the ID but don't commit yet

        # Process ingredients
        recipe_ingredients = []
        for ing_data in recipe_data.ingredients:
            # Check if ingredient already exists by name
            stmt = select(Ingredient).where(Ingredient.ingredient_name == ing_data.name)
            result = await db.execute(stmt)
            ingredient = result.scalars().first()

            # If not, create a new ingredient
            if not ingredient:
                ingredient = Ingredient(
                    id=uuid.uuid4(),
                    ingredient_name=ing_data.name,
                )
                db.add(ingredient)
                await db.flush()

            # Create the recipe-ingredient association
            prep_data = {}
            if ing_data.prep:
                prep_data = {
                    "method": ing_data.prep.method,
                    "size_descriptor": ing_data.prep.size_descriptor,
                }

            recipe_ingredient = RecipeIngredient(
                id=uuid.uuid4(),
                recipe_id=new_recipe.id,
                ingredient_id=ingredient.id,
                # set relationship to avoid lazy-load in response building
                ingredient=ingredient,
                quantity_value=ing_data.quantity_value,
                quantity_unit=ing_data.quantity_unit,
                prep=prep_data,
                is_optional=ing_data.is_optional,
            )
            db.add(recipe_ingredient)
            recipe_ingredients.append(recipe_ingredient)

        # Commit all changes
        await db.commit()

        # Prepare response data
        response_data = {
            "id": new_recipe.id,
            "title": new_recipe.name,
            "description": recipe_data.description,  # Use from input data
            "prep_time_minutes": new_recipe.prep_time_minutes,
            "cook_time_minutes": new_recipe.cook_time_minutes,
            "total_time_minutes": new_recipe.total_time_minutes,
            "serving_min": new_recipe.serving_min,
            "serving_max": new_recipe.serving_max,
            "instructions": new_recipe.instructions,
            # recipe_data.difficulty is already an enum
            "difficulty": recipe_data.difficulty,
            "category": RecipeCategory(new_recipe.course_type),
            "ethnicity": new_recipe.ethnicity,
            "oven_temperature_f": recipe_data.oven_temperature_f,
            "user_notes": new_recipe.user_notes,
            "link_source": new_recipe.link_source,
            # Ensure timestamps present even when DB defaults aren't applied
            # (e.g., when using mocked sessions during tests)
            "created_at": new_recipe.created_at or now_ts,
            "updated_at": new_recipe.updated_at or now_ts,
            "ai_summary": None,  # This would be generated separately
            "ingredients": [
                {
                    "id": str(ri.id),
                    "name": ri.ingredient.ingredient_name,
                    "quantity_value": ri.quantity_value,
                    "quantity_unit": ri.quantity_unit,
                    "prep": ri.prep,
                    "is_optional": ri.is_optional,
                }
                for ri in recipe_ingredients
            ],
        }

        return RecipeOut(**response_data)

    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity error: {str(e)}",
        ) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the recipe: {str(e)}",
        ) from e
