"""Integration tests for the recipes API endpoints."""

import uuid

import pytest
from fastapi import status
from httpx import AsyncClient

from schemas.recipes import RecipeCategory, RecipeDifficulty


@pytest.mark.asyncio
async def test_create_recipe(async_client: AsyncClient) -> None:
    """Test creating a new recipe."""
    # Prepare test data
    recipe_data = {
        "title": "Test Recipe",
        "description": "A test recipe for the integration test",
        "prep_time_minutes": 15,
        "cook_time_minutes": 30,
        "serving_min": 2,
        "serving_max": 4,
        "instructions": ["Step 1", "Step 2", "Step 3"],
        "difficulty": RecipeDifficulty.MEDIUM.value,
        "category": RecipeCategory.DINNER.value,
        "ethnicity": "Italian",
        "oven_temperature_f": 350,
        "user_notes": "Test notes",
        "ingredients": [
            {
                "name": "Test Ingredient 1",
                "quantity_value": 1.0,
                "quantity_unit": "cup",
                "prep": {"method": "chopped", "size_descriptor": "finely"},
                "is_optional": False,
            },
            {
                "name": "Test Ingredient 2",
                "quantity_value": 2.0,
                "quantity_unit": "tbsp",
                "is_optional": True,
            },
        ],
    }

    # Send the request
    response = await async_client.post(
        "/api/v1/recipes/",
        json=recipe_data,
    )

    # Verify response
    assert response.status_code == status.HTTP_201_CREATED

    # Validate response data
    response_data = response.json()
    assert response_data["title"] == recipe_data["title"]
    assert response_data["prep_time_minutes"] == recipe_data["prep_time_minutes"]
    assert response_data["cook_time_minutes"] == recipe_data["cook_time_minutes"]
    assert response_data["total_time_minutes"] == (
        recipe_data["prep_time_minutes"] + recipe_data["cook_time_minutes"]
    )
    assert response_data["serving_min"] == recipe_data["serving_min"]
    assert response_data["serving_max"] == recipe_data["serving_max"]
    assert response_data["instructions"] == recipe_data["instructions"]
    assert response_data["difficulty"] == recipe_data["difficulty"]
    assert response_data["category"] == recipe_data["category"]
    assert response_data["ethnicity"] == recipe_data["ethnicity"]
    assert response_data["oven_temperature_f"] == recipe_data["oven_temperature_f"]
    assert response_data["user_notes"] == recipe_data["user_notes"]

    # Validate ingredients
    assert len(response_data["ingredients"]) == len(recipe_data["ingredients"])

    # Verify IDs are in expected format (UUIDs)
    assert uuid.UUID(response_data["id"])
    for ingredient in response_data["ingredients"]:
        assert uuid.UUID(ingredient["id"])

    # Check ingredient data
    ingredient_names = [i["name"] for i in response_data["ingredients"]]
    assert "Test Ingredient 1" in ingredient_names
    assert "Test Ingredient 2" in ingredient_names

    # Check prep data for first ingredient
    ingredient_1 = next(
        i for i in response_data["ingredients"] if i["name"] == "Test Ingredient 1"
    )
    assert ingredient_1["prep"]["method"] == "chopped"
    assert ingredient_1["prep"]["size_descriptor"] == "finely"
    assert ingredient_1["is_optional"] is False

    # Check optional flag for second ingredient
    ingredient_2 = next(
        i for i in response_data["ingredients"] if i["name"] == "Test Ingredient 2"
    )
    assert ingredient_2["is_optional"] is True
