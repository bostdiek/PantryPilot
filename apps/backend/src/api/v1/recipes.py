"""Recipes API endpoints for the PantryPilot application.

This module defines all recipe-related API endpoints, including CRUD operations
for recipes and their ingredients.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID as UUIDType

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from dependencies.auth import check_resource_access, check_resource_write_access, get_current_user
from dependencies.db import get_db
from models.ingredient_names import Ingredient
from models.recipe_ingredients import RecipeIngredient
from models.recipes_names import Recipe
from models.users import User
from schemas.api import ApiResponse
from schemas.recipes import (
    RecipeCategory,
    RecipeCreate,
    RecipeDifficulty,
    RecipeOut,
    RecipeSearchResponse,
    RecipeUpdate,
)


router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.post(
    "/",
    response_model=ApiResponse[RecipeOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new recipe",
    description=(
        "Create a new recipe with its ingredients, "
        "returning the created recipe with IDs. "
        "Requires authentication."
    ),
    responses={
        201: {"description": "Recipe created successfully"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"},
    },
)
async def create_recipe(
    recipe_data: RecipeCreate, 
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[RecipeOut]:
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
            user_id=current_user.id,  # Set owner
            name=recipe_data.title,
            prep_time_minutes=recipe_data.prep_time_minutes,
            cook_time_minutes=recipe_data.cook_time_minutes,
            total_time_minutes=total_time,
            serving_min=recipe_data.serving_min,
            serving_max=recipe_data.serving_max,
            ethnicity=recipe_data.ethnicity,
            difficulty=recipe_data.difficulty.value,
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
            # Check if ingredient already exists by name for this user
            stmt = select(Ingredient).where(
                and_(
                    Ingredient.ingredient_name == ing_data.name,
                    or_(
                        Ingredient.user_id == current_user.id,
                        Ingredient.user_id.is_(None),  # Legacy ingredients
                    )
                )
            )
            result = await db.execute(stmt)
            ingredient = result.scalars().first()

            # If not, create a new ingredient for this user
            if not ingredient:
                ingredient = Ingredient(
                    id=uuid.uuid4(),
                    user_id=current_user.id,  # Set owner
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
        recipe_response = RecipeOut(**response_data)
        return ApiResponse(
            success=True, data=recipe_response, message="Recipe created successfully"
        )

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
    """Build a RecipeOut schema object from ORM objects.

    Create a Pydantic `RecipeOut` from a SQLAlchemy `Recipe` instance and a list
    of associated `RecipeIngredient` instances.

    Args:
        recipe: The ORM `Recipe` instance containing the primary recipe fields.
        ingredients: List of ORM `RecipeIngredient` instances for this recipe. Each
            item must have its `.ingredient` relationship eagerly loaded (e.g., via
            `selectinload`) so access to `ri.ingredient.ingredient_name` is safe.

    Returns:
        RecipeOut: The validated Pydantic model representing the recipe and its
        ingredient details.

    Notes:
        - This function returns the `RecipeOut` directly and does not wrap it in an
          `ApiResponse`. Callers are responsible for wrapping it at the route layer
          when appropriate.
        - Assumes ingredient relationship objects are already loaded to avoid
          additional database round-trips.
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
        "difficulty": RecipeDifficulty(
            recipe.difficulty or RecipeDifficulty.MEDIUM.value
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


async def _get_or_create_ingredient(db: AsyncSession, name: str, user_id: UUID) -> Ingredient:
    """Return an existing Ingredient by name for the user or create a new one.

    Keeps DB interaction isolated to reduce complexity in route handlers.

    Args:
        db: The SQLAlchemy async session used for queries and persistence.
        name: The ingredient name to look up or create.
        user_id: The user ID to associate with the ingredient.

    Returns:
        Ingredient: The existing (or newly created) `Ingredient` ORM object.

    Raises:
        sqlalchemy.exc.IntegrityError: If a unique/constraint violation occurs while
            creating a new ingredient.
        sqlalchemy.exc.SQLAlchemyError: For other SQLAlchemy-related database errors.
    """
    # Look for ingredient by name for this user or legacy null user_id
    stmt = select(Ingredient).where(
        and_(
            Ingredient.ingredient_name == name,
            or_(
                Ingredient.user_id == user_id,
                Ingredient.user_id.is_(None),  # Legacy ingredients
            )
        )
    )
    result = await db.execute(stmt)
    ingredient = result.scalars().first()
    if not ingredient:
        ingredient = Ingredient(id=uuid.uuid4(), user_id=user_id, ingredient_name=name)
        db.add(ingredient)
        await db.flush()
    return ingredient


async def _replace_recipe_ingredients(
    db: AsyncSession, recipe: Recipe, ingredients_data: list, user_id: UUID
) -> list[RecipeIngredient]:
    """Replace all ingredient associations for a recipe with new ones.

    Removes existing `RecipeIngredient` rows for the given recipe and creates new
    associations from the provided data. New association objects are added to the
    session but not committed.

    Args:
        db: The SQLAlchemy async session used for database operations.
        recipe: The `Recipe` instance whose ingredient associations will be replaced.
        ingredients_data: A list of ingredient input objects (e.g., `IngredientIn`)
            containing name, quantity_value, quantity_unit, optional prep details,
            and optionality flag.

    Returns:
        list[RecipeIngredient]: Newly created association instances corresponding to
        the provided ingredient data. These are attached to the session but not yet
        committed.

    Side Effects:
        - Deletes existing `RecipeIngredient` rows for the recipe.
        - Adds new `RecipeIngredient` rows to the session.

    Note:
        You must call `await db.commit()` in the calling context to persist changes.
    """
    await db.execute(
        delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
    )

    new_ris: list[RecipeIngredient] = []
    for ing in ingredients_data:
        ingredient = await _get_or_create_ingredient(db, ing.name, user_id)

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
    """Apply scalar attribute updates from RecipeUpdate to Recipe in-place.

    Keeps the update loop isolated so the route handler remains small.

    Args:
        recipe: The ORM `Recipe` instance to modify. Modified in-place.
        recipe_data: The `RecipeUpdate` payload containing optional scalar field
            updates. Only provided (non-None) values are applied.
    """
    updatable = {
        "name": recipe_data.title,
        "prep_time_minutes": recipe_data.prep_time_minutes,
        "cook_time_minutes": recipe_data.cook_time_minutes,
        "serving_min": recipe_data.serving_min,
        "serving_max": recipe_data.serving_max,
        "ethnicity": recipe_data.ethnicity,
        "difficulty": recipe_data.difficulty.value if recipe_data.difficulty else None,
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
    response_model=ApiResponse[RecipeSearchResponse],
    summary="Search recipes with optional filters and pagination",
    description=(
        "Return recipes with filters applied and paginated results. "
        "Users can only see their own recipes unless they are an admin. "
        "Requires authentication."
    ),
    responses={
        200: {"description": "Recipes retrieved successfully"},
        401: {"description": "Authentication required"},
    },
)
async def list_recipes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    query: str | None = None,
    difficulty: RecipeDifficulty | None = None,
    max_total_time: int | None = None,
    category: RecipeCategory | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ApiResponse[RecipeSearchResponse]:
    """Return recipes with filters applied and paginated results.

    Notes:
    - difficulty is accepted for future compatibility but not applied because
      there is no difficulty column in the current schema.
    - query matches recipe name and user_notes (as a proxy for description).
    """
    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    filters = []

    # Filter by user ownership (admin can see all recipes)
    if not current_user.is_admin:
        filters.append(
            or_(
                Recipe.user_id == current_user.id,
                Recipe.user_id.is_(None),  # Legacy recipes without owner
            )
        )

    if query:
        like = f"%{query}%"
        filters.append(or_(Recipe.name.ilike(like), Recipe.user_notes.ilike(like)))

    if max_total_time is not None:
        filters.append(Recipe.total_time_minutes <= max_total_time)

    if category is not None:
        filters.append(Recipe.course_type == category.value)

    if difficulty is not None:
        filters.append(Recipe.difficulty == difficulty.value)

    base_q = select(Recipe)
    if filters:
        base_q = base_q.where(and_(*filters))

    # Total count (optional)
    total_stmt = select(func.count()).select_from(Recipe)
    if filters:
        total_stmt = total_stmt.where(and_(*filters))
    total_res = await db.execute(total_stmt)
    total = int(total_res.scalar() or 0)

    # Fetch items with ingredients eager-loaded
    stmt = (
        base_q.options(
            selectinload(Recipe.recipeingredients).selectinload(
                RecipeIngredient.ingredient
            )
        )
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    recipes = result.scalars().all()

    items: list[RecipeOut] = []
    for r in recipes:
        ingredients = list(r.recipeingredients or [])
        items.append(_recipe_to_response(r, ingredients))

    return ApiResponse(
        success=True,
        data=RecipeSearchResponse(items=items, limit=limit, offset=offset, total=total),
        message="Recipes retrieved successfully",
    )


@router.get(
    "/{recipe_id}", 
    response_model=ApiResponse[RecipeOut], 
    summary="Get a recipe by id",
    responses={
        200: {"description": "Recipe retrieved successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Recipe not found or access denied"},
    },
)
async def get_recipe(
    recipe_id: UUIDType,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[RecipeOut]:
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
    
    # Check ownership and access permissions
    recipe = check_resource_access(
        recipe, 
        current_user,
        not_found_message="Recipe not found"
    )

    ingredients = list(recipe.recipeingredients or [])
    recipe_response = _recipe_to_response(recipe, ingredients)
    return ApiResponse(
        success=True, data=recipe_response, message="Recipe retrieved successfully"
    )


@router.put(
    "/{recipe_id}", 
    response_model=ApiResponse[RecipeOut], 
    summary="Update a recipe",
    responses={
        200: {"description": "Recipe updated successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Recipe not found or access denied"},
        422: {"description": "Validation error"},
    },
)
async def update_recipe(
    recipe_id: UUIDType,
    recipe_data: RecipeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[RecipeOut]:
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
    
    # Check write access permissions
    recipe = check_resource_write_access(
        recipe,
        current_user,
        not_found_message="Recipe not found",
        forbidden_message="Not allowed to modify this recipe"
    )

    try:
        # Apply scalar updates
        _apply_scalar_updates(recipe, recipe_data)

        # If ingredients provided, replace associations
        if recipe_data.ingredients is not None:
            await _replace_recipe_ingredients(db, recipe, recipe_data.ingredients, current_user.id)

        await db.commit()
        await db.refresh(recipe)

        # Re-fetch ingredients relationships
        ingredients = list(recipe.recipeingredients or [])
        recipe_response = _recipe_to_response(recipe, ingredients)
        return ApiResponse(
            success=True, data=recipe_response, message="Recipe updated successfully"
        )

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


@router.delete(
    "/{recipe_id}", 
    response_model=ApiResponse[None], 
    summary="Delete a recipe",
    responses={
        200: {"description": "Recipe deleted successfully"},
        401: {"description": "Authentication required"},
        404: {"description": "Recipe not found or access denied"},
    },
)
async def delete_recipe(
    recipe_id: UUIDType,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[None]:
    stmt = select(Recipe).where(Recipe.id == recipe_id)
    result = await db.execute(stmt)
    recipe = result.scalars().first()
    
    # Check delete permissions
    recipe = check_resource_write_access(
        recipe,
        current_user,
        not_found_message="Recipe not found",
        forbidden_message="Not allowed to delete this recipe"
    )

    try:
        # Remove ingredients associations then delete recipe
        await db.execute(
            delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id)
        )
        await db.execute(delete(Recipe).where(Recipe.id == recipe.id))
        await db.commit()
        return ApiResponse(
            success=True, data=None, message="Recipe deleted successfully"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
