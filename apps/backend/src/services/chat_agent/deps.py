"""Chat agent dependencies - shared types for agent and tools."""

from __future__ import annotations

from asyncio import Lock
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
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
    db_lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    @asynccontextmanager
    async def use_db(self) -> AsyncIterator[AsyncSession]:
        """Serialize access to the shared request-scoped async session.

        Pydantic AI may execute multiple tool calls concurrently. SQLAlchemy
        AsyncSession/asyncpg connections cannot process concurrent operations,
        so assistant tools that use the injected session must acquire this guard.
        """
        async with self.db_lock:
            yield self.db
