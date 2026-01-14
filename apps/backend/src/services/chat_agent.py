"""Chat assistant agent construction shared by API and dev tooling."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from pydantic_ai import Agent, RunContext

from schemas.chat_content import AssistantMessage, TextBlock


logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """
You are Nibble, a friendly pantry and meal planning assistant.

Identity rules (critical):
- If asked your name, you MUST answer "Nibble".
- You MUST NOT claim to be Gemini, Google, an LLM, or mention model/provider details.

Output rules (critical):
- You MUST respond using the assistant content block schema.
- Always return at least one TextBlock so the user receives a readable reply.

Tool rules:
- Use tools when they provide factual data (weather lookup or web search).
- Tools are read-only for now; do not claim to take actions.
"""


@lru_cache
def get_chat_agent() -> Agent:
    """Create and cache the chat assistant agent."""
    agent = Agent(
        "gemini-3-flash-preview",
        system_prompt=CHAT_SYSTEM_PROMPT,
        output_type=AssistantMessage,
        name="Nibble",
    )

    @agent.tool
    async def get_daily_weather(
        ctx: RunContext[None],
        location: str,
    ) -> dict[str, Any]:
        """Read-only weather lookup stub."""
        _ = ctx
        logger.debug("Weather tool called for location=%s", location)
        return {
            "location": location,
            "forecast": "Weather lookup is not configured yet.",
        }

    @agent.tool
    async def web_search(ctx: RunContext[None], query: str) -> dict[str, Any]:
        """Read-only web search stub."""
        _ = ctx
        logger.debug("Web search tool called for query=%s", query)
        return {
            "query": query,
            "results": [],
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
