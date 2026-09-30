"""Chat agent dependencies - shared types for agent and tools."""

from __future__ import annotations

from asyncio import Lock
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.user_preferences import UserPreferences
from models.users import User


@dataclass(frozen=True)
class LiveRecipeContext:
    """Authoritative recipe data loaded for a contextual chat run."""

    recipe_id: UUID
    title: str
    description: str | None
    prep_time_minutes: int | None
    cook_time_minutes: int | None
    total_time_minutes: int | None
    serving_min: int | None
    serving_max: int | None
    notes: str | None
    ingredients: tuple[str, ...]
    instructions: tuple[str, ...]


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
    recipe_context: LiveRecipeContext | None = None
    db_lock: Lock = field(default_factory=Lock, repr=False, compare=False)
    retry_budget_lock: Lock = field(default_factory=Lock, repr=False, compare=False)
    failed_tools: set[str] = field(default_factory=set, repr=False, compare=False)
    recovered_tools: set[str] = field(default_factory=set, repr=False, compare=False)
    model_calls_after_failure: dict[str, int] = field(
        default_factory=dict, repr=False, compare=False
    )

    @asynccontextmanager
    async def use_db(self) -> AsyncIterator[AsyncSession]:
        """Serialize access to the shared request-scoped async session.

        Pydantic AI may execute multiple tool calls concurrently. SQLAlchemy
        AsyncSession/asyncpg connections cannot process concurrent operations,
        so assistant tools that use the injected session must acquire this guard.
        """
        async with self.db_lock:
            try:
                yield self.db
            except BaseException:
                await self.db.rollback()
                raise
