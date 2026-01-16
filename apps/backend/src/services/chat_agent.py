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
    async def web_search(ctx: RunContext[ChatAgentDeps], query: str) -> dict[str, Any]:
        """Read-only web search tool (capped)."""
        _ = ctx
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


def _create_chat_agent_for_user() -> Agent[ChatAgentDeps, AssistantMessage]:
    """Create a chat assistant agent with tool support (internal factory).

    This is the underlying agent factory used by both get_chat_agent_with_deps()
    (for dev UX with specific user context) and the cached get_chat_agent() entry point.
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
    async def web_search(ctx: RunContext[ChatAgentDeps], query: str) -> dict[str, Any]:
        """Read-only web search tool (capped)."""
        _ = ctx
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


def get_chat_agent_with_deps(
    user: User, db: AsyncSession | None = None
) -> Agent[ChatAgentDeps, AssistantMessage]:
    """Create a chat agent pre-configured with a specific user (for dev/playground use).

    This creates a new agent (not cached) with tools pre-bound to a specific
    user context. Useful for dev playgrounds and testing scenarios where you
    need user-specific behavior.

    Args:
        user: The User to bind into the agent's context.
        db: Optional AsyncSession to use for tool operations.
             If None, tools may fail (unless you override deps before calling agent).

    Returns:
        An Agent[ChatAgentDeps, AssistantMessage] that is pre-configured for the user.

    Note:
        For dev playgrounds that call agent.to_web(), the web UI will handle session
        management. The db parameter is primarily for custom usage outside of to_web().
    """
    agent = _create_chat_agent_for_user()

    # If db is provided, we need to ensure deps are passed when running
    # the agent. However, agent.to_web() doesn't easily expose a deps
    # override mechanism. For now, return the agent and rely on the caller
    # to pass deps via run_stream_events(). This is a limitation of the
    # current pydanticai web UI - it doesn't support custom deps factory.

    # Workaround: Store db and user on the agent object so the web UI
    # can access them. Note: This is a bit of a hack, but pydanticai's
    # to_web() doesn't provide better options yet
    if db is not None:
        agent._dev_db = db  # type: ignore
        agent._dev_user = user  # type: ignore

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
