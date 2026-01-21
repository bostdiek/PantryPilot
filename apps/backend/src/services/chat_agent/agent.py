"""Chat assistant agent construction shared by API and dev tooling."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from httpx import AsyncClient, HTTPStatusError
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.retries import AsyncTenacityTransport, RetryConfig, wait_retry_after
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry_if_exception_type, stop_after_attempt, wait_exponential

from models.users import User
from schemas.chat_content import AssistantMessage, TextBlock
from services.chat_agent.tools import (
    tool_fetch_url_as_markdown,
    tool_get_daily_weather,
    tool_get_meal_plan_history,
    tool_search_recipes,
    tool_suggest_recipe,
    tool_web_search,
)


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

RECIPE DISCOVERY WORKFLOW:
When users ask for recipe suggestions or want to save a recipe from a website:
1. Use web_search to find relevant recipes if needed
2. Use fetch_url_as_markdown to read the content of promising recipe pages
3. Use suggest_recipe to create a saveable draft with all the recipe details
   - This creates a draft the user can review and add to their collection
   - The tool returns a recipe_card object in its result
   - You MUST include this recipe_card in your response blocks array
   - The recipe card will display an "Add Recipe" button for the user

IMPORTANT: When you find a recipe the user wants, ALWAYS use suggest_recipe
to create a draft. After calling suggest_recipe, include the recipe_card
from the tool result in your blocks array so the user can see and interact
with it.

Output rules (critical):
- You MUST respond using the assistant content block schema.
- Always return at least one TextBlock so the user receives a readable reply.
- When suggest_recipe returns a recipe_card, include it in your blocks array.

Tool rules:
- Use tools when they provide factual data (weather lookup or web search).
- Use suggest_recipe when recommending recipes to create actionable drafts.
- After calling suggest_recipe, add the returned recipe_card to your response blocks.
"""


# ---------------------------------------------------------------------------
# Agent dependencies
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChatAgentDeps:
    """Dependencies injected into the chat agent context."""

    db: AsyncSession
    user: User


# ---------------------------------------------------------------------------
# Agent construction
# ---------------------------------------------------------------------------


def _create_resilient_http_client() -> AsyncClient:
    """Create an HTTP client with exponential backoff retries for transient errors.

    Handles Gemini API overload (503), rate limits (429), and gateway errors.
    Uses exponential backoff with a fallback strategy that respects Retry-After headers.
    """

    def should_retry_status(response: Any) -> None:
        """Raise exceptions for retryable HTTP status codes."""
        if response.status_code in (429, 502, 503, 504):
            response.raise_for_status()

    transport = AsyncTenacityTransport(
        config=RetryConfig(
            retry=retry_if_exception_type(HTTPStatusError),
            wait=wait_retry_after(
                fallback_strategy=wait_exponential(multiplier=2, min=1, max=30),
                max_wait=60,
            ),
            stop=stop_after_attempt(5),
            reraise=True,
        ),
        validate_response=should_retry_status,
    )
    return AsyncClient(transport=transport, timeout=120)


@lru_cache
def get_chat_agent() -> Agent[ChatAgentDeps, AssistantMessage]:
    """Create and cache the chat assistant agent.

    Returns an agent configured with structured output type AssistantMessage.
    Uses `instructions` instead of `system_prompt` because evaluation tooling
    treats this as a standard chat-style agent and dynamically scores runs
    against the full prompt. The recipe extraction agent uses `system_prompt`
    because it is evaluated as a structured task-specific extractor rather
    than a general chat assistant.

    Includes retry logic for transient Gemini API errors (503 overload, etc.)
    with exponential backoff up to 5 attempts.
    """
    # Create HTTP client with retry logic for transient API errors
    http_client = _create_resilient_http_client()
    provider = GoogleProvider(http_client=http_client)
    model = GoogleModel("gemini-2.5-flash", provider=provider)

    agent: Agent[ChatAgentDeps, AssistantMessage] = Agent(
        model,
        instructions=CHAT_SYSTEM_PROMPT,
        output_type=AssistantMessage,
        name="Nibble",
    )

    # Register tools using extracted implementations
    agent.tool(name="get_meal_plan_history")(tool_get_meal_plan_history)
    agent.tool(name="search_recipes")(tool_search_recipes)
    agent.tool(name="get_daily_weather")(tool_get_daily_weather)
    agent.tool(name="web_search")(tool_web_search)
    agent.tool(name="fetch_url_as_markdown")(tool_fetch_url_as_markdown)
    agent.tool(name="suggest_recipe")(tool_suggest_recipe)

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
