"""Image-specific orchestrator for recipe extraction from uploaded photos."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from services.ai.extraction_common import DraftManager
from services.ai.interfaces import (
    AIAgentProtocol,
    AIExtractionService,
    RecipeConverterProtocol,
)
from services.ai.models import DraftOutcome


class ImageOrchestrator(AIExtractionService):
    def __init__(
        self,
        ai_agent: AIAgentProtocol,
        recipe_converter: RecipeConverterProtocol,
        draft_manager: DraftManager,
    ) -> None:
        # Image orchestrator does not need HTML extractor
        self.ai_agent = ai_agent
        self.recipe_converter = recipe_converter
        self.draft_manager = draft_manager

    async def extract_recipe_from_url(
        self,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> DraftOutcome[Any]:
        # Image orchestrator does not implement URL extraction
        raise NotImplementedError()

    async def extract_recipe_from_images(
        self,
        normalized_images: list[bytes],
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> DraftOutcome[Any]:
        try:
            extraction_result = await self.ai_agent.run_image_extraction_agent(
                normalized_images, prompt_override
            )
        except Exception as e:
            from schemas.ai import ExtractionNotFound

            extraction_not_found = ExtractionNotFound(
                reason=f"AI agent error: {str(e)}"
            )
            failure_draft = await self.draft_manager.create_failure_draft(
                db=db,
                current_user=current_user,
                source_url="image_upload",
                extraction_not_found=extraction_not_found,
                prompt_override=prompt_override,
            )
            token = self.draft_manager.create_draft_token(
                failure_draft.id, current_user.id, timedelta(hours=1)
            )
            return DraftOutcome(failure_draft, token, False, message="agent_error")

        from schemas.ai import ExtractionNotFound

        if isinstance(extraction_result, ExtractionNotFound):
            failure_draft = await self.draft_manager.create_failure_draft(
                db=db,
                current_user=current_user,
                source_url="image_upload",
                extraction_not_found=extraction_result,
                prompt_override=prompt_override,
            )
            token = self.draft_manager.create_draft_token(
                failure_draft.id, current_user.id, timedelta(hours=1)
            )
            return DraftOutcome(failure_draft, token, False, message="not_found")

        generated_recipe = self.recipe_converter.convert_to_recipe_create(
            extraction_result, "image_upload"
        )

        draft = await self.draft_manager.create_success_draft(
            db=db,
            current_user=current_user,
            source_url="image_upload",
            generated_recipe=generated_recipe,
            prompt_override=prompt_override,
        )
        token = self.draft_manager.create_draft_token(
            draft.id, current_user.id, timedelta(hours=1)
        )
        return DraftOutcome(draft, token, True)

    def stream_extraction_progress(
        self,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> AsyncGenerator[str, None]:
        # For now, image streaming is not supported here; return an async
        # generator that yields nothing so callers can iterate/await it.
        async def _gen() -> AsyncGenerator[str, None]:
            for _ in ():
                yield ""

        return _gen()
