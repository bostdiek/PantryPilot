from __future__ import annotations

import uuid

import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_create_recipe(async_client):
    """Test creating a recipe with all required fields."""
    # Prepare test data
    payload = {
        "title": "Test Spaghetti",
        "description": "A simple and tasty spaghetti recipe",
        "prep_time_minutes": 10,
        "cook_time_minutes": 20,
        "serving_min": 2,
        "serving_max": 4,
        "instructions": ["Boil water", "Cook pasta", "Add sauce"],
        "difficulty": "medium",
        "category": "dinner",
        "ethnicity": "Italian",
        "oven_temperature_f": None,
        "user_notes": "Family favorite",
        "link_source": None,
        "ingredients": [
            {
                "name": "Spaghetti",
                "quantity_value": 200,
                "quantity_unit": "g",
                "is_optional": False,
                "prep": None,
            },
            {
                "name": "Tomato Sauce",
                "quantity_value": 1,
                "quantity_unit": "cup",
                "is_optional": False,
                "prep": {"method": "heated", "size_descriptor": None},
            },
        ],
    }

    # Send the request — DB is provided by dependency override in conftest
    response = await async_client.post(
        "/api/v1/recipes/",
        json=payload,
    )

    # Assert response
    assert response.status_code == status.HTTP_201_CREATED
    response_wrapper = response.json()

    # Check ApiResponse structure
    assert response_wrapper["success"] is True
    assert "data" in response_wrapper
    assert "message" in response_wrapper

    data = response_wrapper["data"]

    # Validate UUID
    uuid.UUID(data["id"])  # Will raise if not a valid UUID

    # Validate other fields
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["prep_time_minutes"] == payload["prep_time_minutes"]
    assert data["cook_time_minutes"] == payload["cook_time_minutes"]
    expected_total = payload["prep_time_minutes"] + payload["cook_time_minutes"]
    assert data["total_time_minutes"] == expected_total
    assert data["serving_min"] == payload["serving_min"]
    assert data["serving_max"] == payload["serving_max"]
    assert data["difficulty"] == payload["difficulty"]
    assert data["category"] == payload["category"]
    assert data["ethnicity"] == payload["ethnicity"]
    assert data["user_notes"] == payload["user_notes"]

    # Validate ingredients
    assert len(data["ingredients"]) == len(payload["ingredients"])
    for i, ingredient in enumerate(data["ingredients"]):
        assert ingredient["name"] == payload["ingredients"][i]["name"]
        assert (
            ingredient["quantity_value"] == payload["ingredients"][i]["quantity_value"]
        )
        assert ingredient["quantity_unit"] == payload["ingredients"][i]["quantity_unit"]
