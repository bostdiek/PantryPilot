import pytest
from pydantic import ValidationError

from src.schemas.ingredients import IngredientPrepIn, IngredientsIn, IngredientsOut


def test_ingredient_happy_path():
    data = {
        "name": "Tomato",
        "quantity_value": 2.0,
        "quantity_unit": "pcs",
        "prep": {"method": "diced", "size_descriptor": "small"},
        "is_optional": False,
    }

    inst = IngredientsIn(**data)

    assert inst.name == "Tomato"
    assert inst.quantity_value == 2.0
    assert isinstance(inst.prep, IngredientPrepIn)
    assert inst.prep.method == "diced"

    out_data = {**data, "id": "abc123"}
    out = IngredientsOut(**out_data)
    assert out.id == "abc123"


def test_forbid_extra_fields():
    data = {
        "name": "Egg",
        "quantity_value": 1,
        "quantity_unit": "pcs",
        "unknown_field": "should_fail",
    }

    with pytest.raises(ValidationError):
        IngredientsIn(**data)


def test_negative_quantity_invalid():
    data = {"name": "Salt", "quantity_value": -1, "quantity_unit": "g"}

    with pytest.raises(ValidationError):
        IngredientsIn(**data)


def test_missing_name_raises():
    data = {"quantity_value": 1}

    with pytest.raises(ValidationError):
        IngredientsIn(**data)
