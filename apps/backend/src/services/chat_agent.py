"""Chat assistant agent construction shared by API and dev tooling."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from fastapi import HTTPException
from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from schemas.chat_content import AssistantMessage, TextBlock
from services.ai.markdown_extractor import MarkdownExtractionService
from services.weather import get_daily_forecast_for_user
from services.web_search import search_web


logger = logging.getLogger(__name__)

# Lazy initialization for MarkdownExtractionService
_markdown_extractor: MarkdownExtractionService | None = None


def _get_markdown_extractor() -> MarkdownExtractionService:
    global _markdown_extractor
    if _markdown_extractor is None:
        _markdown_extractor = MarkdownExtractionService()
    return _markdown_extractor


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
  their location by saying: "You can set your location in Your Profile
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

    @agent.tool
    async def fetch_url_as_markdown(
        _ctx: RunContext[ChatAgentDeps],
        url: str,
    ) -> dict[str, Any]:
        """Fetch a web page and convert it to readable Markdown.

        Use this tool when you need to read the content of a web page,
        especially recipe pages. The page will be fetched, cleaned of
        navigation and scripts, and converted to Markdown format that
        you can analyze.

        WORKFLOW TIP: After using web_search to find recipe URLs, use this
        tool to read the full recipe content. Then use suggest_recipe to
        create a saveable draft for the user.

        Args:
            url: The URL of the web page to fetch (from web_search results
                 or provided by the user)

        Returns:
            Markdown content of the page that you can analyze to extract
            recipe details like title, ingredients, instructions, etc.
        """
        extractor = _get_markdown_extractor()

        try:
            markdown_content = await extractor.fetch_as_markdown(url)

            if not markdown_content:
                return {
                    "status": "error",
                    "url": url,
                    "content": "",
                    "message": "No content could be extracted from this URL.",
                }

            return {
                "status": "ok",
                "url": url,
                "content": markdown_content,
                "message": (
                    f"Successfully fetched content from {url}. "
                    "Analyze this to extract recipe details."
                ),
            }

        except HTTPException as e:
            return {
                "status": "error",
                "url": url,
                "content": "",
                "message": str(e.detail),
            }
        except Exception as e:
            logger.error(f"Failed to fetch URL as Markdown: {e}")
            return {
                "status": "error",
                "url": url,
                "content": "",
                "message": (
                    "Failed to fetch the URL. Please check if it's a valid web page."
                ),
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
