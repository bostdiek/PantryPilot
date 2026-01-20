"""Chat assistant agent construction shared by API and dev tooling."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from fastapi import HTTPException
from httpx import AsyncClient, HTTPStatusError
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.retries import AsyncTenacityTransport, RetryConfig, wait_retry_after
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry_if_exception_type, stop_after_attempt, wait_exponential

from core.security import create_draft_token
from models.users import User
from schemas.chat_content import AssistantMessage, TextBlock
from schemas.chat_streaming import MAX_SSE_EVENT_BYTES
from services.ai.draft_service import create_success_draft
from services.ai.markdown_extractor import MarkdownExtractionService
from services.weather import get_daily_forecast_for_user
from services.web_search import search_web


logger = logging.getLogger(__name__)

# Maximum content size to avoid SSE payload limits
# Leave room for JSON overhead (url, status, message fields)
MAX_MARKDOWN_CONTENT_CHARS: int = MAX_SSE_EVENT_BYTES - 2000

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

RECIPE DISCOVERY WORKFLOW:
When users ask for recipe suggestions or want to save a recipe from a website:
1. Use web_search to find relevant recipes if needed
2. Use fetch_url_as_markdown to read the content of promising recipe pages
3. Use suggest_recipe to create a saveable draft with all the recipe details
   - This creates a draft the user can review and add to their collection
   - The recipe card will have an "Add Recipe" button

IMPORTANT: When you find a recipe the user wants, ALWAYS use suggest_recipe
to create a draft. Don't just describe the recipe - make it actionable!

Output rules (critical):
- You MUST respond using the assistant content block schema.
- Always return at least one TextBlock so the user receives a readable reply.

Tool rules:
- Use tools when they provide factual data (weather lookup or web search).
- Use suggest_recipe when recommending recipes to create actionable drafts.
"""


# ---------------------------------------------------------------------------
# Tool implementations (extracted for reduced cognitive complexity)
# ---------------------------------------------------------------------------


async def _tool_get_daily_weather(
    ctx: RunContext[ChatAgentDeps],
) -> dict[str, Any]:
    """Read-only weather lookup based on user profile."""
    return await get_daily_forecast_for_user(ctx.deps.db, user_id=ctx.deps.user.id)


async def _tool_web_search(
    _ctx: RunContext[ChatAgentDeps], query: str
) -> dict[str, Any]:
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


async def _tool_fetch_url_as_markdown(
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

        # Truncate content if too large to fit in SSE payload
        was_truncated = False
        if len(markdown_content) > MAX_MARKDOWN_CONTENT_CHARS:
            markdown_content = markdown_content[:MAX_MARKDOWN_CONTENT_CHARS]
            was_truncated = True
            logger.debug(
                f"Truncated markdown content from URL to "
                f"{MAX_MARKDOWN_CONTENT_CHARS} chars"
            )

        message = (
            f"Successfully fetched content from {url}. "
            "Analyze this to extract recipe details."
        )
        if was_truncated:
            message += (
                " Note: Content was truncated due to size limits. "
                "The most important recipe information is usually "
                "at the beginning of the page."
            )

        return {
            "status": "ok",
            "url": url,
            "content": markdown_content,
            "message": message,
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


async def _tool_suggest_recipe(
    ctx: RunContext[ChatAgentDeps],
    title: str,
    description: str,
    prep_time_minutes: int,
    cook_time_minutes: int,
    serving_min: int,
    instructions: list[str],
    category: str,
    ingredients: list[dict[str, Any]],
    source_url: str | None = None,
) -> dict[str, Any]:
    """Suggest a recipe to the user and create a draft for approval.

    Use this when the user asks for recipe suggestions or when you find
    a recipe they might like. Creates a draft that the user can review
    and add to their collection.

    WORKFLOW: After using fetch_url_as_markdown to read a recipe page,
    extract the recipe details and call this tool to create a saveable
    draft. The user will see a recipe card with an "Add Recipe" button.

    Args:
        title: Recipe title
        description: Brief description of the dish
        prep_time_minutes: Preparation time in minutes
        cook_time_minutes: Cooking time in minutes
        serving_min: Minimum number of servings
        instructions: List of cooking instruction steps (each step as a string)
        category: Recipe category - one of: breakfast, lunch, dinner,
                  dessert, snack, appetizer
        ingredients: List of ingredient objects, each with:
            - name (str, required): Ingredient name
            - quantity_value (float, optional): Amount
            - quantity_unit (str, optional): Unit (cups, tbsp, etc.)
            - is_optional (bool, optional): Whether optional
        source_url: Original recipe URL if from external source

    Returns:
        Recipe card data with deep-link for user approval. The card
        includes an "Add Recipe" button that opens a pre-filled form.
    """
    db = ctx.deps.db
    user = ctx.deps.user

    # Build recipe payload
    recipe_data = {
        "title": title,
        "description": description,
        "prep_time_minutes": prep_time_minutes,
        "cook_time_minutes": cook_time_minutes,
        "serving_min": serving_min,
        "instructions": instructions,
        "category": category,
        "ingredients": ingredients,
        "difficulty": "medium",
    }

    if source_url:
        recipe_data["link_source"] = source_url

    try:
        # Create the draft using existing service
        draft = await create_success_draft(
            db=db,
            current_user=user,
            source_url=source_url or "chat://recommendation",
            generated_recipe=recipe_data,
        )

        # Generate signed token for secure access
        token = create_draft_token(draft_id=draft.id, user_id=user.id)

        # Build deep-link URL
        deep_link = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"

        return {
            "status": "ok",
            "recipe_card": {
                "type": "recipe_card",
                "title": title,
                "subtitle": description,
                "image_url": None,
                "href": deep_link,
                "source_url": source_url,  # Original external URL for "View Recipe"
            },
            "message": (
                f"Created recipe draft for '{title}'. "
                "User can click 'Add Recipe' to save it."
            ),
        }

    except Exception as e:
        logger.error(f"Failed to create recipe draft: {e}")
        return {
            "status": "error",
            "recipe_card": None,
            "message": f"Failed to create recipe draft: {e!s}",
        }


# ---------------------------------------------------------------------------
# Agent construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChatAgentDeps:
    db: AsyncSession
    user: User


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
    agent.tool(name="get_daily_weather")(_tool_get_daily_weather)
    agent.tool(name="web_search")(_tool_web_search)
    agent.tool(name="fetch_url_as_markdown")(_tool_fetch_url_as_markdown)
    agent.tool(name="suggest_recipe")(_tool_suggest_recipe)

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
