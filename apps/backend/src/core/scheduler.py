"""Background task scheduler using APScheduler.

Manages scheduled jobs for:
- AI-generated chat title generation (every 10 minutes)
- 90-day chat message retention cleanup (daily at 3 AM UTC)
- 1-hour AI draft expiration cleanup (every 15 minutes)
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from apscheduler.triggers.cron import CronTrigger  # type: ignore
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore
from sqlalchemy import select

from crud.ai_drafts import cleanup_expired_drafts
from dependencies.db import AsyncSessionLocal
from models.chat_conversations import ChatConversation
from models.chat_messages import ChatMessage
from services.chat_retention import enforce_chat_message_retention
from services.chat_title_generator import generate_conversation_title


logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None


async def run_title_generation() -> None:
    """Scheduled job: generate AI titles for conversations with 2+ exchanges.

    Only processes conversations with timestamp-based titles (Chat started ...)
    that have at least 4 messages (2 exchanges).
    """
    logger.info("Starting scheduled title generation job")
    try:
        async with AsyncSessionLocal() as db:
            # Find conversations needing titles
            query = select(ChatConversation).where(
                ChatConversation.title.like("Chat started %")
            )
            result = await db.execute(query)
            conversations = result.scalars().all()

            generated_count = 0
            for conversation in conversations:
                # Get message count for this conversation
                count_query = select(ChatMessage).where(
                    ChatMessage.conversation_id == conversation.id
                )
                count_result = await db.execute(count_query)
                messages = count_result.scalars().all()

                if len(messages) >= 4:  # At least 2 exchanges (4 messages)
                    # Fetch messages for title generation
                    message_dicts = [
                        {"role": msg.role, "content": msg.content or ""}
                        for msg in messages[:6]  # First 3 exchanges
                    ]

                    try:
                        title = await generate_conversation_title(message_dicts)
                        conversation.title = title
                        generated_count += 1
                        conv_id = conversation.id
                        logger.info(
                            f"Generated title for conversation {conv_id}: {title}"
                        )
                    except Exception as e:
                        conv_id = conversation.id
                        logger.error(
                            f"Failed to generate title for conversation {conv_id}: {e}"
                        )
                        continue

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
