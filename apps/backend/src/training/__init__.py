"""Training data generation module for PantryPilot.

This module provides tools for generating synthetic training data using
user personas, query templates, and multi-turn conversation scenarios.
"""

from training.personas import (
    PERSONAS,
    SAMPLE_TARGETS,
    MealPlanHistoryEntry,
    PersonaLocation,
    PersonaPreferences,
    PersonaProfile,
    RecipeData,
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
    get_all_queries,
    get_conversation_scenarios,
    get_follow_ups,
    get_persona_queries,
    get_tool_coverage_queries,
)


__all__ = [
    # Personas
    "PERSONAS",
    "SAMPLE_TARGETS",
    "PersonaLocation",
    "PersonaPreferences",
    "PersonaProfile",
    "RecipeData",
    "MealPlanHistoryEntry",
    "get_persona",
    "get_sample_target",
    "list_persona_names",
    # Query templates
    "PERSONA_QUERIES",
    "CONVERSATION_SCENARIOS",
    "FOLLOW_UP_TYPES",
    "QUERY_TOOL_COVERAGE",
    "format_query",
    "get_all_queries",
    "get_conversation_scenarios",
    "get_follow_ups",
    "get_persona_queries",
    "get_tool_coverage_queries",
]
