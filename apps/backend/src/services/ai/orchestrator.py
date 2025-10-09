"""AI extraction orchestrator"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from schemas.ai import SSEEvent
from services.ai.agents import convert_to_recipe_create, create_recipe_agent
from services.ai.draft_service import (
    create_draft_token,
    create_failure_draft,
    create_success_draft,
)
from services.ai.extraction_common import DraftManager
from services.ai.html_extractor import HTMLExtractionService
from services.ai.image_orchestrator import ImageOrchestrator
from services.ai.interfaces import (
    AIAgentProtocol,
    AIExtractionService,
    DraftServiceProtocol,
    HTMLExtractorProtocol,
    RecipeConverterProtocol,
)
from services.ai.models import DraftOutcome
from services.ai.url_orchestrator import UrlOrchestrator


logger = logging.getLogger(__name__)


class HTMLExtractorAdapter(HTMLExtractorProtocol):
    """Adapter over `HTMLExtractionService` implementing protocol."""

    def __init__(self) -> None:
        self._svc = HTMLExtractionService()

    async def fetch_sanitized_html(self, url: str) -> str:  # noqa: D401
        return await self._svc.fetch_and_sanitize(url)


class AIAgentAdapter(AIAgentProtocol):
    """Adapter wrapping a concrete recipe agent instance."""

    def __init__(self) -> None:
        # Lazy init avoids requiring external model env vars.
        # Tests patch run_extraction_agent; production creates on first use.
        # _agent may be an Agent-like object with an async run method.
        self._agent: Any | None = None
        self._image_agent: Any | None = None

    async def run_extraction_agent(
        self, sanitized_html: str, prompt_override: str | None = None
    ) -> Any:  # noqa: D401, ANN401 (external lib returns Any)
        prompt = (
            prompt_override or "Extract the recipe information from this HTML content:"
        )
        full_prompt = f"{prompt}\n\nHTML Content:\n{sanitized_html}"
        if self._agent is None:  # Lazy creation
            self._agent = create_recipe_agent()
        result: Any = await self._agent.run(full_prompt)
        # pydantic-ai returns object with .output or .data; normalize
        return getattr(result, "output", None) or getattr(result, "data", None)

    async def run_image_extraction_agent(
        self, images: list[bytes], prompt_override: str | None = None
    ) -> Any:  # noqa: D401, ANN401 (external lib returns Any)
        """Run AI agent to extract recipe from image(s) using BinaryContent."""
        from pydantic_ai.messages import BinaryContent

        from services.ai.agents import create_image_recipe_agent

        prompt_text = prompt_override or (
            "Extract the complete recipe information from the provided image(s). "
            "Include all ingredients, instructions, times, and other details "
            "visible in the image."
        )

        # Build message list: prompt first, then BinaryContent for each image
        messages: list[str | BinaryContent] = [prompt_text]
        for img_bytes in images:
            messages.append(BinaryContent(data=img_bytes, media_type="image/jpeg"))

        if self._image_agent is None:  # Lazy creation
            self._image_agent = create_image_recipe_agent()

        result: Any = await self._image_agent.run(messages)
        # pydantic-ai returns object with .output or .data; normalize
        return getattr(result, "output", None) or getattr(result, "data", None)


class RecipeConverterAdapter(RecipeConverterProtocol):
    """Adapter delegating to `convert_to_recipe_create`."""

    def convert_to_recipe_create(self, extraction_result: Any, source_url: str) -> Any:  # noqa: D401
        # extraction_result may be a Pydantic model or mapping; converter
        # returns AIGeneratedRecipe
        return convert_to_recipe_create(extraction_result, source_url)


class DraftServiceAdapter(DraftServiceProtocol):
    """Adapter using draft_service module functions (no dynamic fallbacks)."""

    async def create_success_draft(
        self,
        db: AsyncSession,
        current_user: User,
        source_url: str,
        generated_recipe: Any,
        prompt_override: str | None = None,
    ) -> Any:
        return await create_success_draft(
            db, current_user, source_url, generated_recipe, prompt_override
        )

    async def create_failure_draft(
        self,
        db: AsyncSession,
        current_user: User,
        source_url: str,
        extraction_not_found: Any,
        prompt_override: str | None = None,
    ) -> Any:
        return await create_failure_draft(
            db, current_user, source_url, extraction_not_found, prompt_override
        )

    def create_draft_token(
        self, draft_id: Any, user_id: Any, exp_delta: timedelta | None = None
    ) -> str:
        return create_draft_token(draft_id, user_id, exp_delta)


def _line(event: SSEEvent) -> str:
    return event.to_sse()


class Orchestrator(AIExtractionService):
    """Concrete AI extraction orchestrator using default pipeline implementations.

    Accepts optional protocol implementations to make testing and DI easier.
    """

    def __init__(
        self,
        html_extractor: HTMLExtractorProtocol | None = None,
        ai_agent: AIAgentProtocol | None = None,
        recipe_converter: RecipeConverterProtocol | None = None,
        draft_service: DraftServiceProtocol | None = None,
    ) -> None:
        # Build adapters if not provided (preserve previous behavior)
        html_extractor = html_extractor or HTMLExtractorAdapter()
        ai_agent = ai_agent or AIAgentAdapter()
        recipe_converter = recipe_converter or RecipeConverterAdapter()
        # If a DraftServiceProtocol implementation (e.g., from tests) was
        # provided, use it; otherwise wrap module-level draft helpers via
        # DraftServiceAdapter so DraftManager delegates correctly.
        draft_impl = draft_service or DraftServiceAdapter()
        draft_manager = DraftManager(draft_impl)

        # Compose concrete orchestrators
        self._url = UrlOrchestrator(
            html_extractor, ai_agent, recipe_converter, draft_manager
        )
        self._image = ImageOrchestrator(ai_agent, recipe_converter, draft_manager)

    async def extract_recipe_from_url(
        self,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> DraftOutcome[Any]:
        return await self._url.extract_recipe_from_url(
            source_url, db, current_user, prompt_override
        )

    async def extract_recipe_from_images(
        self,
        normalized_images: list[bytes],
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> DraftOutcome[Any]:
        return await self._image.extract_recipe_from_images(
            normalized_images, db, current_user, prompt_override
        )

    def stream_extraction_progress(
        self,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> AsyncGenerator[str, None]:
        # Route to the appropriate orchestrator based on the form of
        # `source_url`. If it's a UUID-like draft id, delegate to the
        # image orchestrator so image-specific staged events are emitted.
        # Otherwise fall back to the URL orchestrator which implements the
        # HTML fetch -> AI -> convert -> draft flow.
        from uuid import UUID

        try:
            # If source_url parses as UUID, treat as draft id and use image
            # orchestrator's stream implementation.
            UUID(str(source_url))
        except Exception:
            return self._url.stream_extraction_progress(
                source_url, db, current_user, prompt_override
            )

        # It's a draft UUID; route to image orchestrator stream.
        return self._image.stream_extraction_progress(
            source_url, db, current_user, prompt_override
        )


# FastAPI DI provider (used by API layer via Depends)
def get_ai_extraction_service() -> AIExtractionService:
    return Orchestrator()
