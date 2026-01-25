"""Chat agent dependencies - shared types for agent and tools."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from models.user_preferences import UserPreferences
from models.users import User


@dataclass(frozen=True)
class ChatAgentDeps:
    """Dependencies injected into the chat agent context."""

    db: AsyncSession
    user: User
    current_datetime: datetime
    user_timezone: str  # IANA timezone identifier (e.g., 'America/New_York')

    # User context for personalization
    user_preferences: UserPreferences | None = None
    memory_content: str | None = None
