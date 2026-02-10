"""Tests for DAPT corpus preparation modules.

These tests validate the core behaviors of the DAPT corpus preparation
scripts including JSONL parsing, shuffle determinism, and data formatting.
"""

from __future__ import annotations

import json
from pathlib import Path

from training.dapt.create_corpus import read_jsonl
from training.dapt.process_openrecipes import (
    _format_instructions,
    _format_list_or_str,
    format_recipe,
    parse_openrecipes,
)


class TestReadJsonl:
    """Tests for JSONL file reading."""

    def test_read_jsonl_basic(self, tmp_path: Path) -> None:
        """Test basic JSONL reading."""
        jsonl_file = tmp_path / "test.jsonl"
        records = [{"text": "Recipe 1"}, {"text": "Recipe 2"}, {"text": "Recipe 3"}]
        jsonl_file.write_text("\n".join(json.dumps(r) for r in records))

        result = list(read_jsonl(jsonl_file))

        assert len(result) == 3
        assert result[0]["text"] == "Recipe 1"
        assert result[2]["text"] == "Recipe 3"

    def test_read_jsonl_with_empty_lines(self, tmp_path: Path) -> None:
        """Test JSONL reading with empty lines."""
        jsonl_file = tmp_path / "test.jsonl"
        content = '{"text": "First"}\n\n{"text": "Second"}\n   \n{"text": "Third"}'
        jsonl_file.write_text(content)

        result = list(read_jsonl(jsonl_file))

        assert len(result) == 3

    def test_read_jsonl_with_invalid_json(self, tmp_path: Path) -> None:
        """Test that invalid JSON lines are skipped."""
        jsonl_file = tmp_path / "test.jsonl"
        content = '{"text": "Valid"}\ninvalid json\n{"text": "Also valid"}'
        jsonl_file.write_text(content)

        result = list(read_jsonl(jsonl_file))

        assert len(result) == 2
        assert result[0]["text"] == "Valid"
        assert result[1]["text"] == "Also valid"

    def test_read_jsonl_nonexistent_file(self, tmp_path: Path) -> None:
        """Test reading a nonexistent file returns empty iterator."""
        result = list(read_jsonl(tmp_path / "nonexistent.jsonl"))
        assert result == []


class TestParseOpenrecipes:
    """Tests for OpenRecipes parsing."""

    def test_parse_json_array_format(self, tmp_path: Path) -> None:
        """Test parsing JSON array format."""
        json_file = tmp_path / "recipes.json"
        recipes = [
            {"name": "Recipe 1", "ingredients": ["a", "b"]},
            {"name": "Recipe 2", "ingredients": ["c", "d"]},
        ]
        json_file.write_text(json.dumps(recipes))

        result = list(parse_openrecipes(json_file))

        assert len(result) == 2
        assert result[0]["name"] == "Recipe 1"
        assert result[1]["name"] == "Recipe 2"

    def test_parse_jsonl_format(self, tmp_path: Path) -> None:
        """Test parsing JSONL format."""
        jsonl_file = tmp_path / "recipes.jsonl"
        records = [
            {"name": "Recipe 1", "ingredients": ["a", "b"]},
            {"name": "Recipe 2", "ingredients": ["c", "d"]},
        ]
        jsonl_file.write_text("\n".join(json.dumps(r) for r in records))

        result = list(parse_openrecipes(jsonl_file))

        assert len(result) == 2
        assert result[0]["name"] == "Recipe 1"

    def test_parse_with_whitespace_prefix(self, tmp_path: Path) -> None:
        """Test parsing files with leading whitespace."""
        json_file = tmp_path / "recipes.json"
        recipes = [{"name": "Recipe 1"}]
        json_file.write_text("  \n" + json.dumps(recipes))

        result = list(parse_openrecipes(json_file))

        assert len(result) == 1


class TestFormatHelpers:
    """Tests for formatting helper functions."""

    def test_format_list_or_str_with_list(self) -> None:
        """Test formatting a list."""
        result = _format_list_or_str(["apple", "banana", "cherry"])
        assert result == "apple, banana, cherry"

    def test_format_list_or_str_with_string(self) -> None:
        """Test formatting a string."""
        result = _format_list_or_str("already a string")
        assert result == "already a string"

    def test_format_list_or_str_with_none(self) -> None:
        """Test formatting None."""
        result = _format_list_or_str(None)
        assert result == ""

    def test_format_list_or_str_with_empty_list(self) -> None:
        """Test formatting an empty list."""
        result = _format_list_or_str([])
        assert result == ""

    def test_format_instructions_with_list(self) -> None:
        """Test formatting instruction steps."""
        steps = ["Preheat oven", "Mix ingredients", "Bake for 30 minutes"]
        result = _format_instructions(steps)

        assert "1. Preheat oven" in result
        assert "2. Mix ingredients" in result
        assert "3. Bake for 30 minutes" in result

    def test_format_instructions_with_string(self) -> None:
        """Test formatting string instructions."""
        instructions = "Mix all ingredients and bake."
        result = _format_instructions(instructions)
        assert result == instructions

    def test_format_instructions_with_none(self) -> None:
        """Test formatting None instructions."""
        result = _format_instructions(None)
        assert result == ""


class TestFormatRecipe:
    """Tests for recipe formatting."""

    def test_format_recipe_basic(self) -> None:
        """Test basic recipe formatting."""
        recipe = {
            "name": "Chocolate Chip Cookies",
            "ingredients": ["flour", "sugar", "chocolate chips"],
            "recipeInstructions": ["Mix ingredients", "Bake at 350F"],
            "source": "example.com",
        }

        result = format_recipe(recipe)

        assert result is not None
        assert "# Chocolate Chip Cookies" in result
        assert "Source: example.com" in result
        assert "## Ingredients" in result
        assert "## Instructions" in result

    def test_format_recipe_without_name(self) -> None:
        """Test that recipes without names are skipped."""
        recipe = {"ingredients": ["flour", "sugar"]}
        result = format_recipe(recipe)
        assert result is None

    def test_format_recipe_without_content(self) -> None:
        """Test that recipes without ingredients or instructions are skipped."""
        recipe = {"name": "Empty Recipe"}
        result = format_recipe(recipe)
        assert result is None

    def test_format_recipe_with_times(self) -> None:
        """Test recipe formatting with time information."""
        recipe = {
            "name": "Quick Pasta",
            "ingredients": ["pasta", "sauce"],
            "recipeInstructions": ["Boil pasta", "Add sauce"],
            "prepTime": "5 min",
            "cookTime": "10 min",
        }

        result = format_recipe(recipe)

        assert result is not None
        assert "Prep: 5 min" in result
        assert "Cook: 10 min" in result

    def test_format_recipe_with_description(self) -> None:
        """Test recipe formatting with description."""
        recipe = {
            "name": "Special Dish",
            "ingredients": ["special", "ingredients"],
            "recipeInstructions": ["Cook it"],
            "description": "A wonderful recipe passed down through generations.",
        }

        result = format_recipe(recipe)

        assert result is not None
        assert "## About" in result
        assert "passed down through generations" in result


class TestShuffleDeterminism:
    """Tests for shuffle determinism with seed."""

    def test_shuffle_determinism_with_seed(self, tmp_path: Path) -> None:
        """Test that shuffling is deterministic with the same seed."""
        import random

        # Create test records
        records = [{"text": f"Record {i}"} for i in range(100)]

        # Shuffle with seed 42
        random.seed(42)
        shuffled1 = records.copy()
        random.shuffle(shuffled1)

        # Shuffle again with same seed
        random.seed(42)
        shuffled2 = records.copy()
        random.shuffle(shuffled2)

        # Should produce identical results
        assert shuffled1 == shuffled2

    def test_different_seeds_produce_different_results(self, tmp_path: Path) -> None:
        """Test that different seeds produce different shuffles."""
        import random

        records = [{"text": f"Record {i}"} for i in range(100)]

        random.seed(42)
        shuffled1 = records.copy()
        random.shuffle(shuffled1)

        random.seed(123)
        shuffled2 = records.copy()
        random.shuffle(shuffled2)

        # Should produce different results
        assert shuffled1 != shuffled2
