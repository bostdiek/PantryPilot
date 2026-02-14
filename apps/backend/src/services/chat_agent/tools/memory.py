"""Tool for updating user memory document."""

from __future__ import annotations

import logging
from typing import Any

from pydantic_ai import RunContext

from dependencies.db import AsyncSessionLocal
from services.chat_agent.deps import ChatAgentDeps
from services.memory_update import MemoryUpdateService


logger = logging.getLogger(__name__)


async def tool_update_user_memory(
    ctx: RunContext[ChatAgentDeps],
    memory_content: str,
) -> dict[str, Any]:
    """Update the user's memory document with important information to remember.

    Use this tool when you learn something important about the user that should
    be remembered for future conversations. This replaces the entire memory
    document with the new content you provide.

    WHEN TO UPDATE MEMORY:
    - User shares dietary preferences, restrictions, or allergies
    - User mentions family members or household composition
    - User expresses recurring meal preferences (e.g., "We always do pizza Fridays")
    - User shares cooking skill level or time constraints
    - User mentions special occasions or meal traditions
    - User gives feedback about recipes (loved it / hated it)

    WHAT TO INCLUDE:
    Write the memory as a structured markdown document covering:
    - **Family & Household**: Names, ages, preferences of family members
    - **Dietary Notes**: Preferences and restrictions beyond what's in settings
    - **Cooking Style**: Skill level, available time, equipment preferences
    - **Meal Patterns**: Weekly routines, traditions, favorite days for certain foods
    - **Recipe Feedback**: Specific recipes they loved or disliked and why

    IMPORTANT:
    - The memory_content parameter should be the COMPLETE new memory document
    - You are replacing the entire memory, not appending to it
    - Include all previously remembered information that's still relevant
    - Keep the content concise but comprehensive
    - Use markdown formatting for readability
    - Maximum 50,000 characters

    Args:
        memory_content: The complete markdown content for the user's memory
                       document. This replaces any existing content.

    Returns:
        Status indicating success or failure of the memory update.

    Example memory_content:
        '''## Family & Household
        - Family of 4: parents (Alex, Jamie) and two kids (8 and 12)
        - Kids are picky eaters, prefer simple flavors
        - Alex loves spicy food, Jamie prefers mild

        ## Meal Patterns
        - Taco Tuesday is a weekly tradition 🌮
        - Usually eat out on Friday nights
        - Sunday is batch cooking day for the week

        ## Recipe Feedback
        - LOVED the slow cooker beef stew (made it 3 times)
        - Chicken tikka was too spicy for the kids'''
    """
    user = ctx.deps.user

    # Validate memory content length (matches API schema max_length=50000)
    MAX_MEMORY_LENGTH = 50_000
    if len(memory_content) > MAX_MEMORY_LENGTH:
        return {
            "status": "error",
            "message": (
                f"Memory content exceeds maximum length of "
                f"{MAX_MEMORY_LENGTH:,} characters. "
                f"Current length: {len(memory_content):,} characters."
            ),
        }

    try:
        # Use separate database session for write operation
        async with AsyncSessionLocal() as write_db:
            memory_service = MemoryUpdateService(write_db)
            memory_doc = await memory_service.update_memory_content(
                user_id=user.id,
                new_content=memory_content,
                metadata={"source": "agent_tool", "conversation_initiated": True},
            )

        logger.info(
            f"Updated memory for user {user.id} "
            f"(version {memory_doc.version}, {len(memory_content)} chars)"
        )

        return {
            "status": "ok",
            "version": memory_doc.version,
            "message": (
                f"Memory updated successfully (version {memory_doc.version}). "
                "Now respond to the user - do NOT call update_user_memory again."
            ),
        }

    except Exception as e:
        logger.error(f"Failed to update memory for user {user.id}: {e}")
        return {
            "status": "error",
            "message": f"Failed to update memory: {e!s}",
        }
