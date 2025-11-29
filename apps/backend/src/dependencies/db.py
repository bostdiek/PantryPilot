"""Database session dependency using SQLAlchemy async engine.

This sets up an AsyncSession factory bound to the DATABASE_URL.
The engine isn't connected until first use, so importing this module
won't fail if the database isn't running yet.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def _load_env_files() -> None:  # pragma: no cover - side-effect only
    # Import dotenv lazily so the module is optional for users who don't
    # need to load env files. This avoids module-level side effects and
    # keeps mypy from assuming the symbol is always defined.
    try:  # pragma: no cover - optional convenience for local runs
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        return

    # Try to load .env then .env.dev from repo root or any parent directory
    for fname in (".env", ".env.dev"):
        for p in Path(__file__).resolve().parents:
            candidate = p / fname
            if candidate.exists():
                load_dotenv(dotenv_path=candidate, override=False)
                return


def _normalize_asyncpg_url(url: str) -> str:
    """Convert a postgres URL to asyncpg format and fix SSL parameters.

    asyncpg requires 'ssl=require' instead of 'sslmode=require'.
    """
    # Normalize to async driver if a plain postgres URL is provided
    # Accept common prefixes and coerce to asyncpg so we don't require psycopg2
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    elif url.startswith("postgresql+psycopg2://") or url.startswith(
        "postgresql+psycopg://"
    ):
        url = "postgresql+asyncpg://" + url.split("://", 1)[1]

    # asyncpg doesn't accept 'sslmode' parameter, convert to 'ssl'
    # sslmode=require -> ssl=require (for Azure PostgreSQL compatibility)
    url = url.replace("sslmode=require", "ssl=require")
    url = url.replace("sslmode=verify-full", "ssl=verify-full")
    url = url.replace("sslmode=verify-ca", "ssl=verify-ca")
    url = url.replace("sslmode=prefer", "ssl=prefer")
    url = url.replace("sslmode=disable", "ssl=disable")

    return url


def _get_database_url() -> str:
    # Try to load env files for local CLI/dev first
    _load_env_files()

    # 1) Direct DATABASE_URL
    url = os.getenv("DATABASE_URL")
    if url:
        return _normalize_asyncpg_url(url)

    # 2) Construct from POSTGRES_* variables if present
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    if user and password and database:
        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

    # 3) Fallback local default (only used if nothing provided)
    return "postgresql+asyncpg://pantrypilot_dev:dev_password_123@localhost:5432/pantrypilot_dev"


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
