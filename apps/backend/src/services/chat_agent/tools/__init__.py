"""Chat agent tools package."""

from services.chat_agent.tools.meal_history import tool_get_meal_plan_history
from services.chat_agent.tools.meal_proposals import tool_propose_meal_for_day
from services.chat_agent.tools.memory import tool_update_user_memory
from services.chat_agent.tools.recipes import tool_search_recipes
from services.chat_agent.tools.suggestions import tool_suggest_recipe
from services.chat_agent.tools.weather import tool_get_daily_weather
from services.chat_agent.tools.web import tool_fetch_url_as_markdown, tool_web_search


__all__ = [
    "tool_get_meal_plan_history",
    "tool_propose_meal_for_day",
    "tool_search_recipes",
    "tool_suggest_recipe",
    "tool_update_user_memory",
    "tool_get_daily_weather",
    "tool_fetch_url_as_markdown",
    "tool_web_search",
]
