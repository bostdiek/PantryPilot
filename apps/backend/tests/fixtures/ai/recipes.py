"""Recipe-related fixture helpers (Phase 3 fixture split start).

This module begins the decomposition of the monolithic `ai_fixtures` file into
smaller, domain-focused helpers. Only a minimal subset is migrated initially to
validate import patterns. After confirming green tests, additional factories
can be moved incrementally.
"""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from schemas.recipes import IngredientIn, RecipeCategory, RecipeCreate, RecipeDifficulty


def _base_ingredients(count: int = 2) -> list[IngredientIn]:
    return [
        IngredientIn(
            name=f"ingredient_{i}",
            quantity_value=1.0 + i,
            quantity_unit="unit",
            is_optional=False,
        )
        for i in range(count)
    ]


def build_recipe_create(
    title: str = "Test Recipe",
    prep_time_minutes: int = 5,
    cook_time_minutes: int = 10,
    serving_min: int = 2,
    instructions: Iterable[str] | None = None,
    difficulty: RecipeDifficulty = RecipeDifficulty.EASY,
    category: RecipeCategory = RecipeCategory.DINNER,
    ingredient_count: int = 2,
) -> RecipeCreate:
    return RecipeCreate(
        title=title,
        description="Fixture generated recipe",
        prep_time_minutes=prep_time_minutes,
        cook_time_minutes=cook_time_minutes,
        serving_min=serving_min,
        serving_max=serving_min,
        instructions=list(instructions or ["Do thing", "Serve"]),
        difficulty=difficulty,
        category=category,
        ingredients=_base_ingredients(ingredient_count),
    )


@pytest.fixture
def recipe_create_factory():
    def _factory(**overrides):  # type: ignore[no-untyped-def]
        return build_recipe_create(**overrides)

    return _factory
