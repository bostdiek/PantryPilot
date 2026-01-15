"""Service for automatic memory document updates with gating logic."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_memory_documents import UserMemoryDocument


logger = logging.getLogger(__name__)


class MemoryUpdateService:
    """Service for managing automatic memory document updates.

    Implements gating logic to avoid rewriting memory on every message.
    """

    # Gating triggers for memory updates
    PREFERENCE_KEYWORDS = [
        "prefer",
        "like",
        "dislike",
        "hate",
        "love",
        "always",
        "never",
        "allergic",
        "allergy",
        "diet",
        "dietary",
        "restriction",
        "avoid",
        "favorite",
        "favourite",
    ]

    EXPLICIT_MEMORY_KEYWORDS = [
        "remember",
        "don't forget",
        "keep in mind",
        "note that",
        "for future",
    ]

    def __init__(
        self,
        db: AsyncSession,
        message_threshold: int = 10,
    ) -> None:
        """Initialize the memory update service.

        Args:
            db: Database session
            message_threshold: Number of messages before periodic checkpoint
        """
        self.db = db
        self.message_threshold = message_threshold

    async def should_update_memory(
        self,
        user_id: Any,
        message_content: str,
        message_count: int | None = None,
    ) -> bool:
        """Determine if memory should be updated based on gating logic.

        Args:
            user_id: User UUID
            message_content: Content of the user's message
            message_count: Total message count for periodic checkpoint

        Returns:
            True if memory should be updated, False otherwise
        """
        content_lower = message_content.lower()

        # Check for preference language
        if any(keyword in content_lower for keyword in self.PREFERENCE_KEYWORDS):
            logger.debug(
                f"Memory update triggered for user {user_id}: preference keyword",
            )
            return True

        # Check for explicit memory requests
        if any(keyword in content_lower for keyword in self.EXPLICIT_MEMORY_KEYWORDS):
            logger.debug(
                f"Memory update triggered for user {user_id}: explicit memory keyword",
            )
            return True

        # Periodic checkpoint (every N messages)
        if message_count is not None and message_count % self.message_threshold == 0:
            logger.debug(
                f"Memory update triggered for user {user_id}: "
                f"periodic checkpoint at {message_count} messages",
            )
            return True

        return False

    async def update_memory_content(
        self,
        user_id: Any,
        new_content: str,
        metadata: dict[str, Any] | None = None,
    ) -> UserMemoryDocument:
        """Update the memory document content (assistant-initiated).

        Args:
            user_id: User UUID
            new_content: New memory content
            metadata: Optional metadata about the update

        Returns:
            Updated memory document
        """
        # Try to get existing memory document
        stmt = select(UserMemoryDocument).where(UserMemoryDocument.user_id == user_id)
        result = await self.db.execute(stmt)
        memory_doc = result.scalar_one_or_none()

        update_metadata = metadata or {}
        update_metadata["updated_at_iso"] = datetime.now(UTC).isoformat()

        if memory_doc is None:
            # Create new document
            logger.info(f"Creating new memory document for user {user_id} (assistant)")
            memory_doc = UserMemoryDocument(
                user_id=user_id,
                content=new_content,
                format="markdown",
                version=1,
                updated_by="assistant",
                updated_at=datetime.now(UTC),
                metadata_=update_metadata,
            )
            self.db.add(memory_doc)
        else:
            # Update existing document
            logger.info(
                f"Updating memory document for user {user_id} "
                f"(version {memory_doc.version} -> {memory_doc.version + 1}, "
                f"assistant)",
            )
            memory_doc.content = new_content
            memory_doc.version += 1
            memory_doc.updated_by = "assistant"
            memory_doc.updated_at = datetime.now(UTC)
            # Merge new metadata with existing
            current_metadata = memory_doc.metadata_ or {}
            current_metadata.update(update_metadata)
            memory_doc.metadata_ = current_metadata
            # Mark as modified for SQLAlchemy to detect the change
            from sqlalchemy.orm import attributes

            attributes.flag_modified(memory_doc, "metadata_")

        await self.db.commit()
        await self.db.refresh(memory_doc)

        return memory_doc

    async def get_memory_document(
        self,
        user_id: Any,
    ) -> UserMemoryDocument | None:
        """Get the memory document for a user.

        Args:
            user_id: User UUID

        Returns:
            Memory document or None if it doesn't exist
        """
        stmt = select(UserMemoryDocument).where(UserMemoryDocument.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def create_diff_summary(
        old_content: str,
        new_content: str,
    ) -> dict[str, Any]:
        """Create a compact diff summary for SSE events.

        Args:
            old_content: Previous memory content
            new_content: New memory content

        Returns:
            Diff summary with character counts and change indicators
        """
        return {
            "old_length": len(old_content),
            "new_length": len(new_content),
            "changed": old_content != new_content,
            "diff_chars": len(new_content) - len(old_content),
        }
