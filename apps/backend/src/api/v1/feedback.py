"""API endpoints for user feedback on AI responses."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import get_current_user
from dependencies.db import get_db
from models.ai_training_samples import AITrainingSample
from models.users import User
from schemas.ai_training_samples import TrainingSampleFeedback


router = APIRouter(prefix="/messages", tags=["feedback"])

logger = logging.getLogger(__name__)


@router.post("/{message_id}/feedback", status_code=status.HTTP_200_OK)
async def submit_feedback(
    message_id: UUID,
    feedback: TrainingSampleFeedback,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str | UUID]:
    """Submit user feedback (👍/👎) for an assistant message.

    Updates the corresponding training sample for quality signals.
    """
    # Find training sample for this message
    stmt = select(AITrainingSample).where(
        AITrainingSample.message_id == message_id,
        AITrainingSample.user_id == user.id,
    )
    result = await db.execute(stmt)
    sample = result.scalar_one_or_none()

    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training sample not found for this message",
        )

    # Update feedback
    sample.user_feedback = feedback.user_feedback
    await db.commit()

    logger.info(
        "User %s submitted %s feedback for message %s",
        user.id,
        feedback.user_feedback,
        message_id,
    )

    return {
        "status": "ok",
        "message_id": message_id,
        "feedback": feedback.user_feedback,
    }
