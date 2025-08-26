"""Database session dependency using SQLAlchemy async engine.

This sets up an AsyncSession factory bound to the DATABASE_URL.
The engine isn't connected until first use, so importing this module
won't fail if the database isn't running yet.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _get_database_url() -> str:
    # Prefer explicit env; fall back to a sensible local default
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Default dev URL: local postgres
    return "postgresql+asyncpg://pantry_user:secure_password@localhost:5432/pantry_db"


DATABASE_URL = _get_database_url()
engine: AsyncEngine = create_async_engine(DATABASE_URL, future=True, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that provides an AsyncSession and ensures proper cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # Session context manager handles close, but keep explicit for clarity
            await session.close()


DbSession = Annotated[AsyncSession, Depends(get_db)]
