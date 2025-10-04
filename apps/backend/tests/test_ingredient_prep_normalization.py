"""Tests for ingredient preparation normalization in AI extraction conversion."""

from schemas.ai import RecipeExtractionResult
from services.ai.agents import convert_to_recipe_create


def test_sliced_black_olives_normalization() -> None:
    """Ensure 'sliced black olives' splits into name + prep.method."""
    extraction = RecipeExtractionResult(
        title="Test",
        prep_time_minutes=1,
        cook_time_minutes=1,
        serving_min=1,
        instructions=["Do it"],
        difficulty="medium",
        category="dinner",
        ingredients=[
            {
                "name": "sliced black olives",
                "quantity_value": 1.0,
                "quantity_unit": "cup",
                "is_optional": False,
            }
        ],
        confidence_score=0.9,
    )

    generated = convert_to_recipe_create(extraction, "http://example.com")
    ing = generated.recipe_data.ingredients[0]
    # We now accept the AI-provided name/prep verbatim. No automatic
    # normalization is performed by the backend conversion.
    assert ing.name == "sliced black olives"
    assert ing.prep is None
