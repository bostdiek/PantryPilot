"""Tool for weather lookups based on user profile."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from services.chat_agent.deps import ChatAgentDeps
from services.weather import get_daily_forecast_for_user


async def tool_get_daily_weather(
    ctx: RunContext[ChatAgentDeps],
) -> dict[str, Any]:
    """Read-only weather lookup based on user profile."""
    return await get_daily_forecast_for_user(ctx.deps.db, user_id=ctx.deps.user.id)
