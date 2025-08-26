"""Recipes API endpoints for the PantryPilot application.

This module defines all recipe-related API endpoints, including CRUD operations
for recipes and their ingredients.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID as UUIDType

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from dependencies.db import get_db
from models.ingredient_names import Ingredient
from models.recipe_ingredients import RecipeIngredient
from models.recipes_names import Recipe
from schemas.recipes import (
    RecipeCategory,
    RecipeCreate,
    RecipeDifficulty,
    RecipeOut,
    RecipeUpdate,
)


# NOTE: This project does not yet have a user system wired into the Recipe model
# (there is no `user_id` column on `Recipe`). Endpoints below accept an optional
# `current_user` dependency so they can be wired into an auth system later. When
# the `Recipe` model adds `user_id`, the ownership checks will automatically be
# applied by the helpers below.


async def _get_current_user_stub() -> dict | None:
    """Placeholder dependency for current user.

    Replace this with your real `get_current_user` dependency when available.
    Returning None means "no user linked" and endpoints fall back to public
    behaviour (returns all recipes).
    """
    return None


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
        response_data: dict[str, Any] = {
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

        # Pydantic will coerce/validate fields as needed.
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


def _recipe_to_response(
    recipe: Recipe, ingredients: list[RecipeIngredient]
) -> RecipeOut:
    """Build RecipeOut from ORM objects (helper).

    Assumes ingredients list contains RecipeIngredient instances with
    .ingredient relationship loaded.
    """
    now_ts = datetime.now(UTC)
    response_data: dict[str, Any] = {
        "id": recipe.id,
        "title": recipe.name,
        "description": None,
        # Ensure numeric fields are present and of the correct type for Pydantic
        "prep_time_minutes": int(recipe.prep_time_minutes or 0),
        "cook_time_minutes": int(recipe.cook_time_minutes or 0),
        "total_time_minutes": int(recipe.total_time_minutes or 0),
        "serving_min": int(recipe.serving_min or 1),
        "serving_max": recipe.serving_max,
        "instructions": recipe.instructions or [],
        # Provide defaults for enums when the DB value is missing so Pydantic
        # always receives an allowed enum value.
        "difficulty": (
            RecipeDifficulty(recipe.difficulty)
            if getattr(recipe, "difficulty", None)
            else RecipeDifficulty.MEDIUM
        ),
        "category": (
            RecipeCategory(recipe.course_type)
            if recipe.course_type
            else RecipeCategory.LUNCH
        ),
        "ethnicity": recipe.ethnicity,
        "oven_temperature_f": getattr(recipe, "oven_temperature_f", None),
        "user_notes": recipe.user_notes,
        "link_source": recipe.link_source,
        "created_at": recipe.created_at or now_ts,
        "updated_at": recipe.updated_at or now_ts,
        "ai_summary": recipe.ai_summary,
        "ingredients": [],
    }

    # Sanitize ingredient prep dicts to match the Pydantic model shape.
    for ri in ingredients:
        prep_raw: Any = ri.prep or {}
        # Support older keys like `size_unit` by mapping them to `size_descriptor`.
        if isinstance(prep_raw, dict):
            method = prep_raw.get("method")
            size_descriptor = prep_raw.get("size_descriptor") or prep_raw.get(
                "size_unit"
            )
            prep_out = (
                None
                if (method is None and size_descriptor is None)
                else {
                    "method": method,
                    "size_descriptor": size_descriptor,
                }
            )
        else:
            # If the DB stored something unexpected, avoid passing extras to Pydantic
            prep_out = None

        response_data["ingredients"].append(
            {
                "id": ri.id,
                "name": ri.ingredient.ingredient_name,
                "quantity_value": ri.quantity_value,
                "quantity_unit": ri.quantity_unit,
                "prep": prep_out,
                "is_optional": ri.is_optional,
            }
        )

    # Pydantic will coerce/validate fields as needed.
    return RecipeOut(**response_data)


async def _get_or_create_ingredient(db: AsyncSession, name: str) -> Ingredient:
    """Return existing Ingredient by name or create a new one.

    Keeps DB interaction isolated to reduce complexity in route handlers.
    """
    stmt = select(Ingredient).where(Ingredient.ingredient_name == name)
    result = await db.execute(stmt)
    ingredient = result.scalars().first()
    if not ingredient:
        ingredient = Ingredient(id=uuid.uuid4(), ingredient_name=name)
        db.add(ingredient)
        await db.flush()
    return ingredient


async def _replace_recipe_ingredients(
    db: AsyncSession, recipe: Recipe, ingredients_data: list
) -> list[RecipeIngredient]:
    """Remove existing RecipeIngredient rows and create new associations.

    Returns the new RecipeIngredient instances (not committed).
    """
    await db.execute(
        delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
    )

    new_ris: list[RecipeIngredient] = []
    for ing in ingredients_data:
        ingredient = await _get_or_create_ingredient(db, ing.name)

        ri = RecipeIngredient(
            id=uuid.uuid4(),
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            ingredient=ingredient,
            quantity_value=ing.quantity_value,
            quantity_unit=ing.quantity_unit,
            prep={
                "method": ing.prep.method if ing.prep else None,
                "size_descriptor": ing.prep.size_descriptor if ing.prep else None,
            },
            is_optional=ing.is_optional,
        )
        db.add(ri)
        new_ris.append(ri)

    return new_ris


def _apply_scalar_updates(recipe: Recipe, recipe_data: RecipeUpdate) -> None:
    """Apply scalar attribute updates from RecipeUpdate to Recipe.

    Keeps the update loop isolated so the route handler remains small.
    """
    updatable = {
        "name": recipe_data.title,
        "prep_time_minutes": recipe_data.prep_time_minutes,
        "cook_time_minutes": recipe_data.cook_time_minutes,
        "serving_min": recipe_data.serving_min,
        "serving_max": recipe_data.serving_max,
        "ethnicity": recipe_data.ethnicity,
        "course_type": recipe_data.category.value if recipe_data.category else None,
        "instructions": recipe_data.instructions,
        "user_notes": recipe_data.user_notes,
        "link_source": recipe_data.link_source,
    }

    for attr, val in updatable.items():
        if val is not None:
            setattr(recipe, attr, val)


@router.get(
    "/",
    response_model=list[RecipeOut],
    summary="List recipes for the current user (or all recipes if no user linked)",
)
async def list_recipes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict | None, Depends(_get_current_user_stub)] = None,
) -> list[RecipeOut]:
    """Return recipes scoped to current user when available.

    If the `Recipe` model has a `user_id` column, this will filter by it. Until
    a user system is wired, this returns all recipes.
    """
    stmt = select(Recipe).options(
        selectinload(Recipe.recipeingredients).selectinload(RecipeIngredient.ingredient)
    )

    # If the model has a user_id attribute and we have a current_user, filter by it
    if hasattr(Recipe, "user_id") and current_user and "id" in current_user:
        stmt = stmt.where(Recipe.user_id == current_user["id"])  # type: ignore[misc]

    result = await db.execute(stmt)
    recipes = result.scalars().all()

    out: list[RecipeOut] = []
    for r in recipes:
        ingredients = list(r.recipeingredients or [])
        out.append(_recipe_to_response(r, ingredients))

    return out


@router.get("/{recipe_id}", response_model=RecipeOut, summary="Get a recipe by id")
async def get_recipe(
    recipe_id: UUIDType,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict | None, Depends(_get_current_user_stub)] = None,
) -> RecipeOut:
    stmt = (
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.recipeingredients).selectinload(
                RecipeIngredient.ingredient
            )
        )
    )
    result = await db.execute(stmt)
    recipe = result.scalars().first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found"
        )

    # ownership check if user_id exists on model
    if hasattr(Recipe, "user_id") and current_user and "id" in current_user:
        if getattr(recipe, "user_id", None) != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to access this recipe",
            )

    ingredients = list(recipe.recipeingredients or [])
    return _recipe_to_response(recipe, ingredients)


@router.put("/{recipe_id}", response_model=RecipeOut, summary="Update a recipe")
async def update_recipe(
    recipe_id: UUIDType,
    recipe_data: RecipeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict | None, Depends(_get_current_user_stub)] = None,
) -> RecipeOut:
    # Load existing recipe with ingredients
    stmt = (
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.recipeingredients).selectinload(
                RecipeIngredient.ingredient
            )
        )
    )
    result = await db.execute(stmt)
    recipe = result.scalars().first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found"
        )

    if hasattr(Recipe, "user_id") and current_user and "id" in current_user:
        if getattr(recipe, "user_id", None) != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to modify this recipe",
            )

    try:
        # Apply scalar updates
        _apply_scalar_updates(recipe, recipe_data)

        # If ingredients provided, replace associations
        if recipe_data.ingredients is not None:
            await _replace_recipe_ingredients(db, recipe, recipe_data.ingredients)

        await db.commit()
        await db.refresh(recipe)

        # Re-fetch ingredients relationships
        ingredients = list(recipe.recipeingredients or [])
        return _recipe_to_response(recipe, ingredients)

    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.delete("/{recipe_id}", summary="Delete a recipe")
async def delete_recipe(
    recipe_id: UUIDType,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict | None, Depends(_get_current_user_stub)] = None,
) -> Response:
    stmt = select(Recipe).where(Recipe.id == recipe_id)
    result = await db.execute(stmt)
    recipe = result.scalars().first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )

    if hasattr(Recipe, "user_id") and current_user and "id" in current_user:
        if getattr(recipe, "user_id", None) != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to delete this recipe",
            )

    try:
        # Remove ingredients associations then delete recipe
        await db.execute(
            delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
        )
        await db.execute(delete(Recipe).where(Recipe.id == recipe.id))
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
