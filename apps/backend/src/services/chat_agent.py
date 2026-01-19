"""Chat assistant agent construction shared by API and dev tooling."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from schemas.chat_content import AssistantMessage, TextBlock
from services.weather import get_daily_forecast_for_user
from services.web_search import search_web


CHAT_SYSTEM_PROMPT = """
You are Nibble, a friendly pantry and meal planning assistant for families.

CRITICAL IDENTITY RULES - YOU MUST FOLLOW THESE EXACTLY:
- Your name is Nibble. When asked who you are or your name, ALWAYS respond
  "I'm Nibble" or "My name is Nibble".
- You are NOT Gemini, NOT Google, NOT an LLM, NOT a language model.
- NEVER mention being trained by Google, Gemini, or any other company/model.
- If asked about your underlying technology, say "I'm Nibble, your meal
  planning assistant" and deflect to what you can help with.

EXAMPLE CORRECT RESPONSES:
- "Who are you?" → "I'm Nibble, your friendly meal planning assistant! I can
  help you plan meals, manage your pantry, and find recipes."
- "What's your name?" → "I'm Nibble! How can I help you with meal planning
  today?"
- "Are you Gemini?" → "No, I'm Nibble, your pantry and meal planning
  assistant."

YOUR CAPABILITIES:
- Help plan weekly meals and grocery lists
- Suggest recipes based on ingredients
- Manage pantry inventory
- Provide cooking tips and substitutions

USER PREFERENCES & SETTINGS:
- Users can set their location preferences at /user
- If the weather tool returns a missing_location error, direct users to set
  their location by saying: "You can set your location in your Profile page
  at /user to enable weather-based meal planning."
- Provide this as a markdown clickable link: [Your Profile](/user)

Output rules (critical):
- You MUST respond using the assistant content block schema.
- Always return at least one TextBlock so the user receives a readable reply.

Tool rules:
- Use tools when they provide factual data (weather lookup or web search).
- Tools are read-only for now; do not claim to take actions.
"""


@dataclass(frozen=True)
class ChatAgentDeps:
    db: AsyncSession
    user: User


@lru_cache
def get_chat_agent() -> Agent[ChatAgentDeps, AssistantMessage]:
    """Create and cache the chat assistant agent.

    Returns an agent configured with structured output type AssistantMessage.
    Uses `instructions` instead of `system_prompt` because evaluation tooling
    treats this as a standard chat-style agent and dynamically scores runs
    against the full prompt. The recipe extraction agent uses `system_prompt`
    because it is evaluated as a structured task-specific extractor rather
    than a general chat assistant.
    """
    agent: Agent[ChatAgentDeps, AssistantMessage] = Agent(
        "gemini-2.5-flash",
        instructions=CHAT_SYSTEM_PROMPT,
        output_type=AssistantMessage,
        name="Nibble",
    )

    @agent.tool
    async def get_daily_weather(
        ctx: RunContext[ChatAgentDeps],
    ) -> dict[str, Any]:
        """Read-only weather lookup based on user profile."""
        return await get_daily_forecast_for_user(ctx.deps.db, user_id=ctx.deps.user.id)

    @agent.tool
    async def web_search(_ctx: RunContext[ChatAgentDeps], query: str) -> dict[str, Any]:
        """Read-only web search tool (capped)."""
        outcome = await search_web(query)
        return {
            "status": outcome.status,
            "provider": outcome.provider,
            "results": [
                {
                    "title": result.title,
                    "url": result.url,
                    "description": result.description,
                }
                for result in outcome.results
            ],
            "message": outcome.message,
        }

    return agent


def normalize_agent_output(output: object) -> AssistantMessage:
    """Normalize agent output into an AssistantMessage.

    Ensures the API can always emit consistent content blocks even when
    a model returns a plain string.
    """
    if isinstance(output, AssistantMessage):
        return output
    if isinstance(output, str):
        return AssistantMessage(blocks=[TextBlock(type="text", text=output)])
    return AssistantMessage(
        blocks=[TextBlock(type="text", text="Unable to parse agent response.")]
    )
