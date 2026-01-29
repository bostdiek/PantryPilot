"""Background task scheduler using APScheduler.

Manages scheduled jobs for:
- AI-generated chat title generation (every 10 minutes)
- 90-day chat message retention cleanup (daily at 3 AM UTC)
- 1-hour AI draft expiration cleanup (every 15 minutes)
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import (  # type: ignore[import-untyped]
    AsyncIOScheduler,
)
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from apscheduler.triggers.interval import (  # type: ignore[import-untyped]
    IntervalTrigger,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from crud.ai_drafts import cleanup_expired_drafts
from dependencies.db import AsyncSessionLocal
from models.chat_conversations import ChatConversation
from models.chat_messages import ChatMessage
from services.chat_retention import enforce_chat_message_retention
from services.chat_title_generator import generate_conversation_title


logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None


async def _process_conversation_for_title(
    db: AsyncSession, conversation: ChatConversation
) -> str | None:
    """Process a single conversation to generate its title.

    Returns the generated title or None if generation failed.
    """
    # Fetch first 6 messages for title generation (3 exchanges)
    messages_query = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at)
        .limit(6)
    )
    messages_result = await db.execute(messages_query)
    messages = messages_result.scalars().all()

    # Extract text from content_blocks with validation
    message_dicts = []
    for msg in messages:
        text_parts = []

        # Validate content_blocks exists and is iterable
        content_blocks = msg.content_blocks
        if not content_blocks or not isinstance(content_blocks, list):
            logger.warning(f"Message {msg.id} has invalid content_blocks, skipping")
            continue

        # Extract text with validation
        for block in content_blocks:
            if (
                isinstance(block, dict)
                and block.get("type") == "text"
                and "text" in block
            ):
                text_parts.append(str(block["text"]))

        # Only include message if it has content
        if text_parts:
            message_dicts.append(
                {
                    "role": msg.role,
                    "content": " ".join(text_parts),
                }
            )

    # Skip if not enough valid messages
    if len(message_dicts) < 2:
        logger.warning(
            f"Conversation {conversation.id} has insufficient valid messages"
        )
        return None

    # Generate title
    title = await generate_conversation_title(
        message_dicts,
        current_title=conversation.title,
        created_at=conversation.created_at.isoformat()
        if conversation.created_at
        else None,
    )
    return title


async def run_title_generation() -> None:
    """Scheduled job: generate AI titles for conversations with 2+ exchanges.

    Only processes conversations where title_updated_at is NULL
    (meaning title has never been AI-generated) and have at least 4 messages.
    """
    logger.info("Starting scheduled title generation job")
    try:
        async with AsyncSessionLocal() as db:
            # Optimized query: JOIN conversations with message count to avoid N+1
            # Find conversations needing titles with message count >= 4
            query = (
                select(ChatConversation, func.count(ChatMessage.id))
                .join(
                    ChatMessage,
                    ChatConversation.id == ChatMessage.conversation_id,
                    isouter=False,
                )
                .where(ChatConversation.title_updated_at.is_(None))
                .group_by(ChatConversation.id)
                .having(func.count(ChatMessage.id) >= 4)
            )
            result = await db.execute(query)
            conversations_with_count = result.all()

            logger.info(
                f"Found {len(conversations_with_count)} conversations needing titles"
            )

            generated_count = 0
            batch_size = 50  # Process in batches to manage memory

            for idx, (conversation, _msg_count) in enumerate(
                conversations_with_count, start=1
            ):
                try:
                    # Generate title using helper function
                    title = await _process_conversation_for_title(db, conversation)

                    if title is None:
                        continue

                    # Update conversation with generated title
                    conversation.title = title
                    conversation.title_updated_at = datetime.now(UTC)
                    generated_count += 1
                    conv_id = conversation.id
                    logger.info(f"Generated title for conversation {conv_id}: {title}")

                    # Batch commit every batch_size conversations
                    if idx % batch_size == 0:
                        await db.commit()
                        logger.info(f"Batch committed: {generated_count} titles so far")

                except Exception as e:
                    conv_id = conversation.id
                    logger.error(
                        f"Failed to generate title for conversation {conv_id}: {e}"
                    )
                    continue

            # Final commit for remaining conversations
            if generated_count > 0:
                await db.commit()
                logger.info(
                    f"Title generation completed: {generated_count} titles generated"
                )
            else:
                logger.info(
                    "Title generation completed: no conversations needed titles"
                )

    except Exception as e:
        logger.error(f"Title generation job failed: {e}", exc_info=True)


async def run_chat_cleanup() -> None:
    """Scheduled job: enforce 90-day chat message retention."""
    logger.info("Starting scheduled chat message cleanup")
    try:
        async with AsyncSessionLocal() as db:
            deleted = await enforce_chat_message_retention(db)
            logger.info(f"Chat cleanup completed: {deleted} messages deleted")
    except Exception as e:
        logger.error(f"Chat cleanup failed: {e}", exc_info=True)


async def run_draft_cleanup() -> None:
    """Scheduled job: clean up expired AI drafts (1-hour TTL)."""
    try:
        async with AsyncSessionLocal() as db:
            deleted = await cleanup_expired_drafts(db)
            if deleted > 0:
                logger.info(f"AI draft cleanup: {deleted} drafts deleted")
    except Exception as e:
        logger.error(f"AI draft cleanup failed: {e}", exc_info=True)


def setup_scheduler() -> AsyncIOScheduler:
    """Initialize APScheduler with all background jobs.

    Jobs:
    - Title generation: Every 10 minutes
    - Chat cleanup: Daily at 3:00 AM UTC (90-day retention)
    - Draft cleanup: Every 15 minutes (1-hour expiration)
    """
    global scheduler
    scheduler = AsyncIOScheduler(timezone="UTC")

    # AI title generation - every 10 minutes
    scheduler.add_job(
        run_title_generation,
        trigger=IntervalTrigger(minutes=10),
        id="generate_chat_titles",
        name="AI chat title generation",
        replace_existing=True,
    )

    # 90-day chat cleanup - daily at 3:00 AM UTC
    scheduler.add_job(
        run_chat_cleanup,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_chat_messages",
        name="90-day chat message retention",
        replace_existing=True,
    )

    # AI draft cleanup - every 15 minutes
    scheduler.add_job(
        run_draft_cleanup,
        trigger=IntervalTrigger(minutes=15),
        id="cleanup_ai_drafts",
        name="Expired AI draft cleanup",
        replace_existing=True,
    )

    logger.info(
        "Scheduler configured: title generation (10 min), "
        "chat cleanup (daily 3 AM), draft cleanup (15 min)"
    )
    return scheduler


@asynccontextmanager
async def scheduler_lifespan() -> AsyncGenerator[None, None]:
    """Context manager for scheduler lifecycle.

    Usage in FastAPI:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with scheduler_lifespan():
                yield
    """
    setup_scheduler()
    if scheduler:
        scheduler.start()
        logger.info("Background scheduler started")
    try:
        yield
    finally:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("Background scheduler shut down")
