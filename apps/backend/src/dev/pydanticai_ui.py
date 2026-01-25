"""Run the PydanticAI Web Chat UI for the chat assistant (dev only)."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import uvicorn
from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.security import get_password_hash
from crud.user import UserCRUD
from crud.user_preferences import UserPreferencesCRUD
from models.base import Base
from schemas.chat_content import AssistantMessage
from schemas.user_preferences import UserPreferencesUpdate
from services.chat_agent import CHAT_SYSTEM_PROMPT
from services.weather import get_daily_forecast_for_user
from services.web_search import search_web


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetachedDevUser:
    """Minimal user info that survives outside SQLAlchemy session scope."""

    id: UUID
    username: str


# NOTE: Module-level mutable state for dev UI only.
# These globals are intentionally reset in main() before starting uvicorn to ensure
# they are created fresh in uvicorn's event loop. This pattern is NOT thread-safe
# and should NOT be used in production code. It works here because:
#   1. The dev UI runs in a single process with a single event loop
#   2. main() explicitly resets these before starting the server
#   3. _get_session_factory() lazily initializes them in uvicorn's loop
#
# For production deployments, use proper dependency injection via FastAPI's
# Depends() mechanism, as demonstrated in the main API router.
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_local_database_url() -> str:
    """Build a database URL suitable for local (non-Docker) execution.

    When running outside of Docker, the 'db' hostname won't resolve.
    This function constructs a connection string using 'localhost' instead.
    """
    user = os.getenv("POSTGRES_USER", "pantrypilot_dev")
    password = os.getenv("POSTGRES_PASSWORD", "dev_password_123")
    db = os.getenv("POSTGRES_DB", "pantrypilot_dev")
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"postgresql+asyncpg://{user}:{password}@localhost:{port}/{db}"


async def ensure_dev_user() -> DetachedDevUser:
    """Ensure a 'dev' user exists with location for testing weather tool.

    Creates the dev user and preferences within a properly managed session,
    then returns a DetachedDevUser with essential attributes. The session and
    engine are cleaned up before returning to avoid resource leaks.

    Returns:
        A DetachedDevUser with id and username attributes.
    """
    database_url = _get_local_database_url()
    logger.info("Connecting to database at localhost...")
    engine = create_async_engine(database_url, echo=False)

    try:
        # Create tables if needed
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create session factory
        async_session_local = async_sessionmaker(
            engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

        async with async_session_local() as db:
            user_crud = UserCRUD()
            dev_user = await user_crud.get_by_username(db, "dev")

            if not dev_user:
                logger.info("Creating dev user...")
                hashed_pw = get_password_hash("dev_password_123")
                dev_user = await user_crud.create(
                    db=db,
                    email="dev@pantrypilot.local",
                    username="dev",
                    hashed_password=hashed_pw,
                    first_name="Dev",
                    last_name="User",
                )
                logger.info(f"Created dev user: {dev_user.id}")

            # Ensure dev user has location preferences for weather testing
            prefs_crud = UserPreferencesCRUD()
            dev_prefs = await prefs_crud.get_by_user_id(db, dev_user.id)

            if dev_prefs is None:
                logger.info("Creating dev user preferences with location...")
                prefs_create = UserPreferencesUpdate(
                    city="Boston",
                    state_or_region="MA",
                    postal_code="02101",
                    country="US",
                    latitude=42.3601,
                    longitude=-71.0589,
                    timezone="America/New_York",
                )
                dev_prefs = await prefs_crud.create(db, dev_user.id, prefs_create)
                logger.info(
                    "Created dev preferences with location: %s, %s",
                    dev_prefs.city,
                    dev_prefs.state_or_region,
                )
            elif not dev_prefs.latitude or not dev_prefs.longitude:
                logger.info("Updating dev user preferences with location...")
                prefs_update = UserPreferencesUpdate(
                    city="Boston",
                    state_or_region="MA",
                    postal_code="02101",
                    country="US",
                    latitude=42.3601,
                    longitude=-71.0589,
                    timezone="America/New_York",
                )
                dev_prefs = await prefs_crud.update(db, dev_prefs, prefs_update)
                logger.info(
                    "Updated dev preferences with location: %s, %s",
                    dev_prefs.city,
                    dev_prefs.state_or_region,
                )

            # Detach user from session before returning
            # Copy essential attributes to survive session close
            user_id = dev_user.id
            username = dev_user.username

        return DetachedDevUser(id=user_id, username=username)
    finally:
        await engine.dispose()


def _create_dev_agent(user_id: UUID) -> Agent[None, AssistantMessage]:
    """Create a dev-specific agent with tool_plain decorators.

    PydanticAI's to_web() doesn't support passing dependencies to tools,
    so we use tool_plain decorators and create the DB session lazily
    within the same event loop that uvicorn uses.
    """

    def _get_session_factory() -> async_sessionmaker[AsyncSession]:
        """Lazily create engine and session factory in the current event loop."""
        global _engine, _session_factory
        if _session_factory is None:
            database_url = _get_local_database_url()
            _engine = create_async_engine(database_url, echo=False)
            _session_factory = async_sessionmaker(
                _engine,
                expire_on_commit=False,
                class_=AsyncSession,
            )
        return _session_factory

    agent = Agent(
        "gemini-2.5-flash",
        instructions=CHAT_SYSTEM_PROMPT,
        output_type=AssistantMessage,
        name="Nibble (Dev)",
    )

    @agent.tool_plain
    async def get_daily_weather() -> dict[str, Any]:
        """Get the 7-day weather forecast for the user's location."""
        factory = _get_session_factory()
        async with factory() as db:
            return await get_daily_forecast_for_user(db, user_id=user_id)

    @agent.tool_plain
    async def web_search(query: str) -> dict[str, Any]:
        """Search the web for recipes and cooking information."""
        outcome = await search_web(query)
        return {
            "status": outcome.status,
            "provider": outcome.provider,
            "results": [
                {
                    "title": result.title,
                    "url": result.url,
                    "description": result.description,
                }
                for result in outcome.results
            ],
            "message": outcome.message,
        }

    return agent


def main() -> None:
    """Launch the PydanticAI Web Chat UI for local agent iteration."""
    logging.basicConfig(level=logging.INFO)

    # Ensure dev user exists with location (runs in a temporary event loop)
    dev_user = asyncio.run(ensure_dev_user())
    logger.info(f"Using dev user: {dev_user.username} ({dev_user.id})")

    # Reset the global engine so it gets created fresh in uvicorn's loop
    global _engine, _session_factory
    _engine = None
    _session_factory = None

    # Create a dev-specific agent with tool_plain decorators
    # The engine will be created lazily in uvicorn's event loop
    agent = _create_dev_agent(dev_user.id)
    app = agent.to_web()
    logger.info("Starting PydanticAI Web UI at http://127.0.0.1:8021")
    logger.info("Tools available: get_daily_weather, web_search")
    uvicorn.run(app, host="127.0.0.1", port=8021)


if __name__ == "__main__":
    main()
