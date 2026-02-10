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
    response_wrapper = response.json()
    assert response_wrapper["success"] is True
    assert "data" in response_wrapper

    response_data = response_wrapper["data"]
    assert response_data["title"] == recipe_data["title"]
    assert response_data["description"] == recipe_data["description"]
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


@pytest.mark.asyncio
async def test_search_recipes_compact_default(async_client: AsyncClient) -> None:
    """Test that search returns compact results by default for token efficiency."""
    # Search for recipes (default should be compact)
    response = await async_client.get("/api/v1/recipes/?query=test")

    assert response.status_code == status.HTTP_200_OK

    response_wrapper = response.json()
    assert response_wrapper["success"] is True
    assert "data" in response_wrapper

    data = response_wrapper["data"]

    # Verify it's a compact response
    assert "items" in data
    assert "limit" in data
    assert "offset" in data
    assert "total" in data

    # If there are results, verify they have compact fields only
    if data["items"]:
        item = data["items"][0]
        # Compact fields should be present
        assert "id" in item
        assert "title" in item

        # Full recipe fields should NOT be present in compact mode
        assert "ingredients" not in item or item.get("ingredients") is None
        assert "instructions" not in item or item.get("instructions") is None


@pytest.mark.asyncio
async def test_search_recipes_full_when_requested(async_client: AsyncClient) -> None:
    """Test that include_full_recipe=true returns complete recipe data."""
    # Search with full recipe requested
    response = await async_client.get(
        "/api/v1/recipes/?query=test&include_full_recipe=true"
    )

    assert response.status_code == status.HTTP_200_OK

    response_wrapper = response.json()
    assert response_wrapper["success"] is True

    data = response_wrapper["data"]
    assert "items" in data

    # If there are results, verify they have full recipe details
    if data["items"]:
        item = data["items"][0]
        # Full recipe fields should be present
        assert "id" in item
        assert "title" in item
        # When full recipe is true, ingredients and instructions should be included
        # (Note: May be empty arrays but fields should exist)
        assert "ingredients" in item
        assert "instructions" in item


@pytest.mark.asyncio
async def test_search_recipes_token_efficiency(async_client: AsyncClient) -> None:
    """Verify compact search uses significantly fewer tokens than full search."""
    try:
        import tiktoken
    except ImportError:
        pytest.skip("tiktoken not available")

    encoding = tiktoken.get_encoding("cl100k_base")

    import json

    # Get compact results
    compact_response = await async_client.get(
        "/api/v1/recipes/?limit=10&include_full_recipe=false"
    )
    compact_json = compact_response.json()
    compact_tokens = len(
        encoding.encode(json.dumps(compact_json, separators=(",", ":"), sort_keys=True))
    )

    # Get full results
    full_response = await async_client.get(
        "/api/v1/recipes/?limit=10&include_full_recipe=true"
    )
    full_json = full_response.json()
    full_tokens = len(
        encoding.encode(json.dumps(full_json, separators=(",", ":"), sort_keys=True))
    )

    # Compact should use significantly fewer tokens
    # We expect at least 30% reduction when recipes exist
    if compact_json["data"]["items"]:
        token_reduction_pct = ((full_tokens - compact_tokens) / full_tokens) * 100
        assert token_reduction_pct >= 30, (
            f"Compact search should reduce tokens by at least 30%, "
            f"but only reduced by {token_reduction_pct:.1f}% "
            f"(compact: {compact_tokens}, full: {full_tokens})"
        )
