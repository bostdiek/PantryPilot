"""Chat agent dependencies - shared types for agent and tools."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User


@dataclass(frozen=True)
class ChatAgentDeps:
    """Dependencies injected into the chat agent context."""

    db: AsyncSession
    user: User
