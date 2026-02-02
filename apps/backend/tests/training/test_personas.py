"""Tests for persona definitions and query templates.

These tests validate that persona data is complete and properly structured
for training data generation.
"""

from datetime import datetime

import pytest

from training.personas import (
    PERSONAS,
    SAMPLE_TARGETS,
    get_persona,
    get_sample_target,
    list_persona_names,
)
from training.query_templates import (
    CONVERSATION_SCENARIOS,
    FOLLOW_UP_TYPES,
    PERSONA_QUERIES,
    QUERY_TOOL_COVERAGE,
    format_query,
    get_conversation_scenarios,
    get_persona_queries,
)


class TestPersonaDefinitions:
    """Tests for persona profile completeness and structure."""

    def test_all_personas_have_required_fields(self) -> None:
        """Verify all personas have required top-level fields."""
        required_fields = {
            "user_id",
            "preferences",
            "recipes",
            "meal_plan_history",
            "pantry_items",
        }

        for persona_name, persona in PERSONAS.items():
            missing = required_fields - set(persona.keys())
            assert not missing, f"Persona {persona_name} missing fields: {missing}"

    def test_all_personas_have_preference_fields(self) -> None:
        """Verify all personas have required preference fields."""
        required_prefs = {
            "dietary_restrictions",
            "cuisine_preferences",
            "cooking_skill",
            "household_size",
            "location",  # Required for weather tool
        }

        for persona_name, persona in PERSONAS.items():
            prefs = persona["preferences"]
            missing = required_prefs - set(prefs.keys())
            assert not missing, (
                f"Persona {persona_name} missing preference fields: {missing}"
            )

    def test_all_personas_have_location_fields(self) -> None:
        """Verify all personas have required location fields for weather tool."""
        required_location = {"city", "state_or_region", "country", "postal_code"}

        for persona_name, persona in PERSONAS.items():
            location = persona["preferences"]["location"]
            missing = required_location - set(location.keys())
            assert not missing, (
                f"Persona {persona_name} missing location fields: {missing}"
            )
            # Verify values are non-empty strings
            for field in required_location:
                assert location[field], (
                    f"Persona {persona_name} has empty location.{field}"
                )

    def test_minimum_recipe_count(self) -> None:
        """Verify each persona has at least 10 recipes."""
        min_recipes = 10

        for persona_name, persona in PERSONAS.items():
            recipe_count = len(persona["recipes"])
            assert recipe_count >= min_recipes, (
                f"Persona {persona_name} has {recipe_count} recipes, "
                f"minimum is {min_recipes}"
            )

    def test_recipe_structure(self) -> None:
        """Verify recipes have required fields."""
        for persona_name, persona in PERSONAS.items():
            for i, recipe in enumerate(persona["recipes"]):
                assert "name" in recipe, (
                    f"Persona {persona_name} recipe {i} missing 'name'"
                )
                assert "tags" in recipe, (
                    f"Persona {persona_name} recipe {i} missing 'tags'"
                )
                assert isinstance(recipe["tags"], list), (
                    f"Persona {persona_name} recipe {i} 'tags' must be a list"
                )

    def test_meal_plan_history_dates_are_valid(self) -> None:
        """Verify meal plan history entries have valid dates."""
        for persona_name, persona in PERSONAS.items():
            for i, entry in enumerate(persona["meal_plan_history"]):
                assert "date" in entry, (
                    f"Persona {persona_name} history {i} missing 'date'"
                )
                # Verify date format is valid
                try:
                    datetime.strptime(entry["date"], "%Y-%m-%d")
                except ValueError:
                    pytest.fail(
                        f"Persona {persona_name} history {i} has invalid date: "
                        f"{entry['date']}"
                    )

    def test_meal_plan_history_has_meal_type(self) -> None:
        """Verify meal plan history entries have meal type."""
        valid_meals = {"breakfast", "lunch", "dinner"}

        for persona_name, persona in PERSONAS.items():
            for i, entry in enumerate(persona["meal_plan_history"]):
                assert "meal" in entry, (
                    f"Persona {persona_name} history {i} missing 'meal'"
                )
                assert entry["meal"] in valid_meals, (
                    f"Persona {persona_name} history {i} has invalid meal: "
                    f"{entry['meal']}"
                )

    def test_minimum_meal_plan_history(self) -> None:
        """Verify each persona has at least 5 days of meal history."""
        min_history = 5

        for persona_name, persona in PERSONAS.items():
            history_count = len(persona["meal_plan_history"])
            assert history_count >= min_history, (
                f"Persona {persona_name} has {history_count} history entries, "
                f"minimum is {min_history}"
            )

    def test_minimum_pantry_items(self) -> None:
        """Verify each persona has at least 8 pantry items."""
        min_pantry = 8

        for persona_name, persona in PERSONAS.items():
            pantry_count = len(persona["pantry_items"])
            assert pantry_count >= min_pantry, (
                f"Persona {persona_name} has {pantry_count} pantry items, "
                f"minimum is {min_pantry}"
            )

    def test_cooking_skill_is_valid(self) -> None:
        """Verify cooking skill levels are valid."""
        valid_skills = {"beginner", "intermediate", "advanced"}

        for persona_name, persona in PERSONAS.items():
            skill = persona["preferences"]["cooking_skill"]
            assert skill in valid_skills, (
                f"Persona {persona_name} has invalid cooking skill: {skill}"
            )

    def test_household_size_is_positive(self) -> None:
        """Verify household sizes are positive integers."""
        for persona_name, persona in PERSONAS.items():
            size = persona["preferences"]["household_size"]
            assert isinstance(size, int) and size > 0, (
                f"Persona {persona_name} has invalid household size: {size}"
            )

    def test_expected_persona_count(self) -> None:
        """Verify we have exactly 8 personas as designed."""
        assert len(PERSONAS) == 8, f"Expected 8 personas, found {len(PERSONAS)}"

    def test_sample_targets_exist_for_all_personas(self) -> None:
        """Verify sample targets defined for all personas."""
        for persona_name in PERSONAS:
            assert persona_name in SAMPLE_TARGETS, (
                f"Missing sample target for persona: {persona_name}"
            )

    def test_sample_targets_sum_to_approximately_1000(self) -> None:
        """Verify total sample target is approximately 1000."""
        total = sum(SAMPLE_TARGETS.values())
        assert 900 <= total <= 1100, f"Total sample target is {total}, expected ~1000"


class TestPersonaFunctions:
    """Tests for persona accessor functions."""

    def test_get_persona_returns_correct_persona(self) -> None:
        """Verify get_persona returns the correct profile."""
        persona = get_persona("veggie_val")
        assert persona["user_id"] == "synthetic-veggie-val"

    def test_get_persona_raises_on_invalid_name(self) -> None:
        """Verify get_persona raises KeyError for unknown persona."""
        with pytest.raises(KeyError):
            get_persona("nonexistent_persona")

    def test_list_persona_names_returns_all_personas(self) -> None:
        """Verify list_persona_names returns all persona keys."""
        names = list_persona_names()
        assert set(names) == set(PERSONAS.keys())

    def test_get_sample_target_returns_correct_value(self) -> None:
        """Verify get_sample_target returns correct counts."""
        # Family Fiona has the highest target (200)
        assert get_sample_target("family_fiona") == 200


class TestQueryTemplates:
    """Tests for query template completeness."""

    def test_queries_exist_for_all_personas(self) -> None:
        """Verify query templates exist for all personas."""
        for persona_name in PERSONAS:
            assert persona_name in PERSONA_QUERIES, (
                f"Missing query templates for persona: {persona_name}"
            )

    def test_minimum_query_count_per_persona(self) -> None:
        """Verify each persona has at least 10 query templates."""
        min_queries = 10

        for persona_name, queries in PERSONA_QUERIES.items():
            query_count = len(queries)
            assert query_count >= min_queries, (
                f"Persona {persona_name} has {query_count} queries, "
                f"minimum is {min_queries}"
            )

    def test_conversation_scenarios_exist_for_all_personas(self) -> None:
        """Verify conversation scenarios exist for all personas."""
        for persona_name in PERSONAS:
            assert persona_name in CONVERSATION_SCENARIOS, (
                f"Missing conversation scenarios for persona: {persona_name}"
            )

    def test_conversation_scenarios_have_multiple_turns(self) -> None:
        """Verify conversation scenarios have at least 2 turns each."""
        for persona_name, scenarios in CONVERSATION_SCENARIOS.items():
            assert len(scenarios) >= 2, (
                f"Persona {persona_name} needs at least 2 conversation scenarios"
            )
            for i, scenario in enumerate(scenarios):
                assert len(scenario) >= 2, (
                    f"Persona {persona_name} scenario {i} needs at least 2 turns"
                )

    def test_tool_coverage_exists_for_all_personas(self) -> None:
        """Verify tool coverage mapping exists for all personas."""
        for persona_name in PERSONAS:
            assert persona_name in QUERY_TOOL_COVERAGE, (
                f"Missing tool coverage for persona: {persona_name}"
            )

    def test_tool_coverage_includes_core_tools(self) -> None:
        """Verify tool coverage includes all 8 agent tools from agent.py."""
        # All 8 tools from apps/backend/src/services/chat_agent/agent.py
        all_tools = {
            "search_recipes",
            "get_meal_plan_history",
            "get_daily_weather",
            "web_search",
            "fetch_url_as_markdown",
            "suggest_recipe",
            "propose_meal_for_day",
            "update_user_memory",
        }

        for persona_name, coverage in QUERY_TOOL_COVERAGE.items():
            missing = all_tools - set(coverage.keys())
            assert not missing, (
                f"Persona {persona_name} missing tool coverage for: {missing}"
            )

    def test_follow_up_types_defined(self) -> None:
        """Verify follow-up query types are defined."""
        expected_types = {
            "refinement",
            "clarification",
            "selection",
            "action",
            "history",
        }
        assert set(FOLLOW_UP_TYPES.keys()) == expected_types


class TestQueryFormatting:
    """Tests for query template formatting."""

    def test_format_query_substitutes_variables(self) -> None:
        """Verify format_query substitutes placeholders correctly."""
        template = "I want to make something with {pantry_item} tonight"
        result = format_query(template, {"pantry_item": "tofu"})
        assert result == "I want to make something with tofu tonight"

    def test_format_query_handles_multiple_variables(self) -> None:
        """Verify format_query handles multiple placeholders."""
        template = "Make a {cuisine} dish with {ingredient}"
        result = format_query(template, {"cuisine": "Italian", "ingredient": "pasta"})
        assert result == "Make a Italian dish with pasta"

    def test_format_query_raises_on_missing_variable(self) -> None:
        """Verify format_query raises KeyError for missing variables."""
        template = "I need {ingredient}"
        with pytest.raises(KeyError):
            format_query(template, {})

    def test_get_persona_queries_returns_list(self) -> None:
        """Verify get_persona_queries returns a list of strings."""
        queries = get_persona_queries("veggie_val")
        assert isinstance(queries, list)
        assert all(isinstance(q, str) for q in queries)

    def test_get_conversation_scenarios_returns_list_of_lists(self) -> None:
        """Verify get_conversation_scenarios returns nested lists."""
        scenarios = get_conversation_scenarios("family_fiona")
        assert isinstance(scenarios, list)
        for scenario in scenarios:
            assert isinstance(scenario, list)
            assert all(isinstance(q, str) for q in scenario)


class TestPersonaDiversity:
    """Tests for persona diversity and coverage."""

    def test_dietary_restrictions_are_diverse(self) -> None:
        """Verify personas cover different dietary restrictions."""
        all_restrictions: set[str] = set()
        for persona in PERSONAS.values():
            all_restrictions.update(persona["preferences"]["dietary_restrictions"])

        # Should include at least vegetarian, gluten-free, dairy-free, high-protein
        expected = {"vegetarian", "gluten-free", "dairy-free", "high-protein"}
        covered = expected & all_restrictions
        assert len(covered) >= 3, f"Need more dietary diversity, only found: {covered}"

    def test_household_sizes_are_diverse(self) -> None:
        """Verify personas cover different household sizes."""
        sizes = {p["preferences"]["household_size"] for p in PERSONAS.values()}
        # Should include at least single (1), couple (2), and family (4+)
        assert 1 in sizes, "Need a single-person household"
        assert 2 in sizes, "Need a couple household"
        assert any(s >= 4 for s in sizes), "Need a large family household"

    def test_cooking_skills_are_diverse(self) -> None:
        """Verify personas cover different cooking skill levels."""
        skills = {p["preferences"]["cooking_skill"] for p in PERSONAS.values()}
        expected = {"beginner", "intermediate", "advanced"}
        assert skills == expected, f"Missing cooking skill levels: {expected - skills}"

    def test_cuisine_preferences_are_diverse(self) -> None:
        """Verify personas cover different cuisine preferences."""
        all_cuisines: set[str] = set()
        for persona in PERSONAS.values():
            all_cuisines.update(persona["preferences"]["cuisine_preferences"])

        # Should have at least 5 different cuisine categories
        assert len(all_cuisines) >= 5, (
            f"Need more cuisine diversity, only found: {all_cuisines}"
        )
