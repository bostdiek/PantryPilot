"""CRUD operations for grocery list generation."""

from collections import defaultdict
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from models.ingredient_names import Ingredient
from models.meal_history import Meal
from models.recipe_ingredients import RecipeIngredient
from models.recipes_names import Recipe
from schemas.grocery_lists import GroceryListIngredient, GroceryListResponse


class GroceryListCRUD:
    """CRUD operations for grocery list generation."""

    async def generate_grocery_list(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> GroceryListResponse:
        """Generate a grocery list for the given user and date range.

        Args:
            db: Database session
            user_id: User identifier
            start_date: Start date for grocery list (inclusive)
            end_date: End date for grocery list (inclusive)

        Returns:
            GroceryListResponse with aggregated ingredients and metadata
        """
        # First, get all meals in the date range that have recipes
        meals_stmt = (
            select(Meal)
            .where(
                and_(
                    Meal.user_id == user_id,
                    Meal.planned_for_date >= start_date,
                    Meal.planned_for_date <= end_date,
                    Meal.recipe_id.is_not(None),  # Only meals with recipes
                    Meal.is_eating_out.is_(False),  # Exclude eating out
                )
            )
            .options(joinedload(Meal.recipe))
        )

        meals_result = await db.execute(meals_stmt)
        meals = list(meals_result.scalars().unique().all())

        if not meals:
            # Return empty grocery list if no meals found
            return GroceryListResponse(
                start_date=start_date,
                end_date=end_date,
                ingredients=[],
                total_meals=0,
            )

        # Get recipe IDs from the meals
        recipe_ids = [meal.recipe_id for meal in meals if meal.recipe_id]

        # Get all ingredients for the recipes with their details
        ingredients_stmt = (
            select(
                RecipeIngredient.quantity_value,
                RecipeIngredient.quantity_unit,
                Ingredient.id.label("ingredient_id"),
                Ingredient.ingredient_name.label("ingredient_name"),
                Recipe.name.label("recipe_name"),
            )
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .join(Recipe, RecipeIngredient.recipe_id == Recipe.id)
            .where(
                and_(
                    RecipeIngredient.recipe_id.in_(recipe_ids),
                    # Exclude optional ingredients
                    RecipeIngredient.is_optional.is_(False),
                    # Must have quantity
                    RecipeIngredient.quantity_value.is_not(None),
                    # Must have unit
                    RecipeIngredient.quantity_unit.is_not(None),
                )
            )
        )

        ingredients_result = await db.execute(ingredients_stmt)
        ingredient_rows = ingredients_result.fetchall()

        # Aggregate ingredients by (ingredient_id, unit) combination
        aggregated: dict[tuple[UUID, str], dict[str, Any]] = defaultdict(
            lambda: {
                "quantity_value": 0.0,
                "recipes": set(),
                "ingredient_name": "",
                "ingredient_id": None,
            }
        )

        for row in ingredient_rows:
            key = (row.ingredient_id, row.quantity_unit)
            agg = aggregated[key]

            # Add to quantity (convert to float for aggregation)
            agg["quantity_value"] += float(row.quantity_value or 0)
            agg["recipes"].add(row.recipe_name)
            agg["ingredient_name"] = row.ingredient_name
            agg["ingredient_id"] = row.ingredient_id

        # Convert aggregated data to response format
        grocery_ingredients = []
        for (_ingredient_id, unit), data in aggregated.items():
            grocery_ingredients.append(
                GroceryListIngredient(
                    id=data["ingredient_id"],
                    name=data["ingredient_name"],
                    quantity_value=data["quantity_value"],
                    quantity_unit=unit,
                    recipes=sorted(list(data["recipes"])),
                )
            )

        # Sort ingredients by name for consistent output
        grocery_ingredients.sort(key=lambda x: x.name.lower())

        return GroceryListResponse(
            start_date=start_date,
            end_date=end_date,
            ingredients=grocery_ingredients,
            total_meals=len(meals),
        )


# Singleton instance to use across the application
grocery_list_crud = GroceryListCRUD()
