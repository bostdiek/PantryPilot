"""API endpoints for user memory document management."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import get_current_user
from dependencies.db import get_db
from models.user_memory_documents import UserMemoryDocument
from models.users import User
from schemas.user_memory_document import (
    UserMemoryDocumentResponse,
    UserMemoryDocumentUpdate,
    UserMemoryDocumentUpdateResponse,
)


router = APIRouter(prefix="/chat/memory", tags=["chat", "memory"])
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=UserMemoryDocumentResponse,
    summary="Get user memory document",
    description="Retrieve the user's memory document maintained by the assistant",
)
async def get_user_memory_document(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserMemoryDocument:
    """Get the current user's memory document.

    If no memory document exists, creates an empty one.
    """
    # Try to get existing memory document
    stmt = select(UserMemoryDocument).where(
        UserMemoryDocument.user_id == current_user.id
    )
    result = await db.execute(stmt)
    memory_doc = result.scalar_one_or_none()

    # Create empty document if none exists
    if memory_doc is None:
        logger.info(
            f"Creating new memory document for user {current_user.id}",
        )
        memory_doc = UserMemoryDocument(
            user_id=current_user.id,
            content="",
            format="markdown",
            version=1,
            updated_by="user",
            updated_at=datetime.now(UTC),
            metadata_={},
        )
        db.add(memory_doc)
        await db.commit()
        await db.refresh(memory_doc)

    return memory_doc


@router.put(
    "",
    response_model=UserMemoryDocumentUpdateResponse,
    summary="Update user memory document",
    description="Update the user's memory document content (user-initiated edit)",
)
async def update_user_memory_document(
    update: UserMemoryDocumentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserMemoryDocument:
    """Update the current user's memory document.

    Creates a new document if none exists. Increments version and marks
    updated_by as 'user'.
    """
    # Try to get existing memory document
    stmt = select(UserMemoryDocument).where(
        UserMemoryDocument.user_id == current_user.id
    )
    result = await db.execute(stmt)
    memory_doc = result.scalar_one_or_none()

    if memory_doc is None:
        # Create new document
        logger.info(
            f"Creating new memory document for user {current_user.id} via update",
        )
        memory_doc = UserMemoryDocument(
            user_id=current_user.id,
            content=update.content,
            format="markdown",
            version=1,
            updated_by="user",
            updated_at=datetime.now(UTC),
            metadata_={},
        )
        db.add(memory_doc)
    else:
        # Update existing document
        logger.info(
            f"Updating memory document for user {current_user.id} "
            f"(version {memory_doc.version} -> {memory_doc.version + 1})",
        )
        memory_doc.content = update.content
        memory_doc.version += 1
        memory_doc.updated_by = "user"
        memory_doc.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(memory_doc)

    return memory_doc
