"""CRUD operations for AI drafts."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_drafts import AIDraft


async def create_draft(
    db: AsyncSession,
    user_id: UUID,
    draft_type: str,
    payload: dict[str, Any],
    source_url: str | None = None,
    prompt_used: str | None = None,
    ttl_hours: int = 1,
) -> AIDraft:
    """Create a new AI draft.
    
    Args:
        db: Database session
        user_id: User ID who owns the draft
        draft_type: Type of draft (e.g., "recipe_suggestion")
        payload: JSON payload containing the draft data
        source_url: Optional source URL if extracted from web
        prompt_used: Optional prompt that was used for generation
        ttl_hours: Time to live in hours (default 1 hour)
        
    Returns:
        Created AIDraft instance
    """
    expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
    
    draft = AIDraft(
        user_id=user_id,
        type=draft_type,
        payload=payload,
        source_url=source_url,
        prompt_used=prompt_used,
        expires_at=expires_at,
    )
    
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    
    return draft


async def get_draft_by_id(
    db: AsyncSession, 
    draft_id: UUID,
    user_id: UUID | None = None
) -> AIDraft | None:
    """Get an AI draft by ID.
    
    Args:
        db: Database session
        draft_id: Draft ID to retrieve
        user_id: Optional user ID for ownership check
        
    Returns:
        AIDraft instance or None if not found
    """
    query = select(AIDraft).where(AIDraft.id == draft_id)
    
    if user_id is not None:
        query = query.where(AIDraft.user_id == user_id)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def delete_draft(
    db: AsyncSession, 
    draft_id: UUID,
    user_id: UUID | None = None
) -> bool:
    """Delete an AI draft.
    
    Args:
        db: Database session
        draft_id: Draft ID to delete
        user_id: Optional user ID for ownership check
        
    Returns:
        True if deleted, False if not found
    """
    draft = await get_draft_by_id(db, draft_id, user_id)
    if not draft:
        return False
    
    await db.delete(draft)
    await db.commit()
    return True


async def cleanup_expired_drafts(db: AsyncSession) -> int:
    """Clean up expired AI drafts.
    
    Args:
        db: Database session
        
    Returns:
        Number of drafts deleted
    """
    now = datetime.now(UTC)
    query = select(AIDraft).where(AIDraft.expires_at < now)
    
    result = await db.execute(query)
    expired_drafts = result.scalars().all()
    
    count = len(expired_drafts)
    for draft in expired_drafts:
        await db.delete(draft)
    
    await db.commit()
    return count


async def get_user_drafts(
    db: AsyncSession,
    user_id: UUID,
    draft_type: str | None = None,
    include_expired: bool = False
) -> list[AIDraft]:
    """Get all drafts for a user.
    
    Args:
        db: Database session
        user_id: User ID to get drafts for
        draft_type: Optional type filter
        include_expired: Whether to include expired drafts
        
    Returns:
        List of AIDraft instances
    """
    query = select(AIDraft).where(AIDraft.user_id == user_id)
    
    if draft_type is not None:
        query = query.where(AIDraft.type == draft_type)
    
    if not include_expired:
        query = query.where(AIDraft.expires_at > datetime.now(UTC))
    
    result = await db.execute(query)
    return list(result.scalars().all())