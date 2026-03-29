"""Chat agent package - AI assistant for meal planning."""

from services.chat_agent.agent import (
    CHAT_SYSTEM_PROMPT,
    build_datetime_instructions as build_datetime_instructions,
    build_user_context_instructions as build_user_context_instructions,
    get_chat_agent,
    normalize_agent_output,
)
from services.chat_agent.deps import ChatAgentDeps
from services.chat_agent.schemas import (
    DayOfWeekMeals,
    MealEntry,
    MealPlanHistoryResponse,
    TimelineDayMeals,
)


__all__ = [
    # Agent construction
    "ChatAgentDeps",
    "CHAT_SYSTEM_PROMPT",
    "build_datetime_instructions",
    "build_user_context_instructions",
    "get_chat_agent",
    "normalize_agent_output",
    # Schemas
    "DayOfWeekMeals",
    "MealEntry",
    "MealPlanHistoryResponse",
    "TimelineDayMeals",
]
