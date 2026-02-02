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
    """Generate a title from the conversation messages.

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
        user_messages = [m for m in messages if m.get("role") == "user"]
        if len(user_messages) < 3:
            if current_title:
                return current_title
            raise ValueError("Not enough conversation context to generate title")

        # Format all messages, trimming to keep a reasonable prompt size.
        formatted_lines: list[str] = []
        total_chars = 0
        max_total_chars = 20000
        for message in messages:
            content = message.get("content", "")
            if not content:
                continue
            snippet = content[:200]
            line = f"{message.get('role', 'unknown')}: {snippet}"
            if total_chars + len(line) + 1 > max_total_chars:
                break
            formatted_lines.append(line)
            total_chars += len(line) + 1

        formatted = "\n".join(formatted_lines)

        # Include current title context if available
        context = f"Generate a title for:\n{formatted}"
        if current_title and created_at:
            context = (
                f"Current title: '{current_title}' (created {created_at})\n\n{context}"
            )

        logger.info(f"Generating title for conversation with {len(messages)} messages")

        agent = _get_title_agent()
        result = await agent.run(context)

        logger.info(f"Generated title: {result.output.title}")
        return result.output.title

    except Exception as e:
        logger.error(f"Failed to generate conversation title: {e}", exc_info=True)
        raise
