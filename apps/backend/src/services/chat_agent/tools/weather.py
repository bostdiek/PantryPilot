"""Tool for weather lookups based on user profile."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from crud.user_preferences import user_preferences_crud
from services.chat_agent.deps import ChatAgentDeps
from services.weather import get_daily_forecast_for_preferences


async def tool_get_daily_weather(
    ctx: RunContext[ChatAgentDeps],
) -> dict[str, Any]:
    """Read-only weather lookup based on user profile."""
    async with ctx.deps.use_db() as db:
        preferences = await user_preferences_crud.get_by_user_id(db, ctx.deps.user.id)
    return await get_daily_forecast_for_preferences(
        user_id=ctx.deps.user.id,
        preferences=preferences,
    )
