from __future__ import annotations

import uuid

import pytest


@pytest.mark.skip(
    reason="Requires running DB; enable when integration DB fixture is ready"
)
def test_create_recipe_minimal(client):
    payload = {
        "title": "Test Spaghetti",
        "description": "tasty",
        "category": "Dinner",
        "prepTime": 10,
        "cookTime": 20,
        "servings": 4,
        "ingredients": ["spaghetti", "tomato"],
        "instructions": ["Boil water", "Cook pasta"],
    }
    resp = client.post("/api/v1/recipes", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "data" in body
    data = body["data"]
    # ensure id is a uuid string
    uuid.UUID(data["id"])  # will raise if not a valid uuid
    assert data["title"] == payload["title"]
    assert data["servings"] == payload["servings"]
