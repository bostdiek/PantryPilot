"""Service for generating AI-powered chat titles using pydantic-ai."""

import logging

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from services.ai.model_factory import get_text_model


logger = logging.getLogger(__name__)


class GeneratedTitle(BaseModel):
    """Structured output for AI-generated conversation title."""

    title: str = Field(
        description="3-5 word title with one food emoji",
        max_length=60,
    )


TITLE_SYSTEM_PROMPT = """Generate a concise 3-5 word title for this cooking
assistant chat.

Rules:
- Focus on the recipe, ingredient, or meal planning topic
- Use the conversation's primary language
- Output JSON only: {"title": "🍳 Your Title"}

Examples:
{"title": "Weekly Meal Planning for week of {date}"}
{"title": "Quick Pasta Ideas"}
{"title": "Leftover Chicken Recipes"}
"""

# Lazy-load the agent to avoid requiring API keys at import time
_title_agent: Agent[None, GeneratedTitle] | None = None


def _get_title_agent() -> Agent[None, GeneratedTitle]:
    """Get or create the title generation agent (lazy initialization).

    Uses centralized model factory for provider selection and credential
    validation.
    """
    global _title_agent
    if _title_agent is None:
        model = get_text_model()
        _title_agent = Agent(
            model,
            output_type=GeneratedTitle,
            system_prompt=TITLE_SYSTEM_PROMPT,
        )
    return _title_agent


async def generate_conversation_title(
    messages: list[dict[str, str]],
    current_title: str | None = None,
    created_at: str | None = None,
) -> str:
    """Generate a title from the first 3 exchanges (6 messages).

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        current_title: The current conversation title (often timestamp-based)
        created_at: ISO timestamp when conversation was created

    Returns:
        Generated title string (3-5 words with food emoji)

    Raises:
        Exception: If AI generation fails
    """
    try:
        # Format first 6 messages (3 exchanges)
        # Limit content to first 200 chars per message for token efficiency
        formatted = "\n".join(
            f"{m['role']}: {m['content'][:200]}" for m in messages[:6]
        )

        # Include current title context if available
        context = f"Generate a title for:\n{formatted}"
        if current_title and created_at:
            context = (
                f"Current title: '{current_title}' (created {created_at})\n\n{context}"
            )

        logger.info(
            f"Generating title for conversation with {len(messages[:6])} messages"
        )

        agent = _get_title_agent()
        result = await agent.run(context)

        logger.info(f"Generated title: {result.output.title}")
        return result.output.title

    except Exception as e:
        logger.error(f"Failed to generate conversation title: {e}", exc_info=True)
        raise
