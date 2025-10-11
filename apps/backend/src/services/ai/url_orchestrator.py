"""URL-specific orchestrator for recipe extraction from HTML pages."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from schemas.ai import SSEEvent
from services.ai.extraction_common import DraftManager
from services.ai.interfaces import (
    AIAgentProtocol,
    AIExtractionService,
    HTMLExtractorProtocol,
    RecipeConverterProtocol,
)
from services.ai.models import DraftOutcome


class UrlOrchestrator(AIExtractionService):
    def __init__(
        self,
        html_extractor: HTMLExtractorProtocol,
        ai_agent: AIAgentProtocol,
        recipe_converter: RecipeConverterProtocol,
        draft_manager: DraftManager,
    ) -> None:
        self.html_extractor = html_extractor
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
        sanitized_html = await self.html_extractor.fetch_sanitized_html(source_url)
        if not sanitized_html:
            from schemas.ai import ExtractionNotFound

            failure_draft = await self.draft_manager.create_failure_draft(
                db=db,
                current_user=current_user,
                source_url=source_url,
                extraction_not_found=ExtractionNotFound(reason="fetch_failed"),
                prompt_override=prompt_override,
            )
            token = self.draft_manager.create_draft_token(
                failure_draft.id,
                current_user.id,
                timedelta(hours=1),
            )
            return DraftOutcome(failure_draft, token, False, message="fetch_failed")

        extraction_result = await self.ai_agent.run_extraction_agent(
            sanitized_html, prompt_override
        )

        from schemas.ai import ExtractionNotFound

        if isinstance(extraction_result, ExtractionNotFound):
            failure_draft = await self.draft_manager.create_failure_draft(
                db=db,
                current_user=current_user,
                source_url=source_url,
                extraction_not_found=extraction_result,
                prompt_override=prompt_override,
            )
            token = self.draft_manager.create_draft_token(
                failure_draft.id,
                current_user.id,
                timedelta(hours=1),
            )
            return DraftOutcome(failure_draft, token, False, message="not_found")

        generated_recipe = self.recipe_converter.convert_to_recipe_create(
            extraction_result, source_url
        )

        draft = await self.draft_manager.create_success_draft(
            db=db,
            current_user=current_user,
            source_url=source_url,
            generated_recipe=generated_recipe,
            prompt_override=prompt_override,
        )
        token = self.draft_manager.create_draft_token(
            draft.id,
            current_user.id,
            timedelta(hours=1),
        )
        return DraftOutcome(draft, token, True)

    async def extract_recipe_from_images(
        self,
        normalized_images: list[bytes],
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> DraftOutcome[Any]:
        # URL orchestrator does not implement image extraction
        raise NotImplementedError()

    async def stream_extraction_progress(
        self,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> AsyncGenerator[str, None]:
        yield (
            SSEEvent.model_validate(
                {"status": "started", "step": "started", "progress": 0.0}
            ).to_sse()
        )
        yield (
            SSEEvent.model_validate(
                {"status": "fetching", "step": "fetch_html", "progress": 0.1}
            ).to_sse()
        )

        try:
            html = await self.html_extractor.fetch_sanitized_html(source_url)
        except Exception as e:
            yield (
                SSEEvent.terminal_error(
                    step="fetch_html",
                    detail=f"Fetch failed: {e}",
                    error_code="fetch_failed",
                ).to_sse()
            )
            return

        if not html:
            yield (
                SSEEvent.terminal_error(
                    step="fetch_html",
                    detail="No usable HTML content",
                    error_code="empty_html",
                ).to_sse()
            )
            return

        yield (
            SSEEvent.model_validate(
                {"status": "sanitizing", "step": "sanitize_html", "progress": 0.25}
            ).to_sse()
        )

        yield (
            SSEEvent.model_validate(
                {"status": "ai_call", "step": "ai_call", "progress": 0.5}
            ).to_sse()
        )
        try:
            extraction_result = await self.ai_agent.run_extraction_agent(
                html, prompt_override
            )
        except Exception as e:
            yield (
                SSEEvent.terminal_error(
                    step="ai_call",
                    detail=f"AI agent failure: {e}",
                    error_code="agent_error",
                ).to_sse()
            )
            return

        from schemas.ai import ExtractionNotFound

        if isinstance(extraction_result, ExtractionNotFound):
            draft_obj = await self.draft_manager.create_failure_draft(
                db,
                current_user,
                source_url,
                extraction_result,
                prompt_override,
            )
            yield (
                SSEEvent.terminal_success(
                    draft_id=getattr(draft_obj, "id", None), success=False
                ).to_sse()
            )
            return

        try:
            generated_recipe = self.recipe_converter.convert_to_recipe_create(
                extraction_result, source_url
            )
        except Exception as e:
            yield (
                SSEEvent.terminal_error(
                    step="convert_schema",
                    detail=f"Conversion failed: {e}",
                    error_code="convert_failed",
                ).to_sse()
            )
            return

        yield (
            SSEEvent.model_validate(
                {"status": "converting", "step": "convert_schema", "progress": 0.75}
            ).to_sse()
        )

        draft_obj = await self.draft_manager.create_success_draft(
            db,
            current_user,
            source_url,
            generated_recipe,
            prompt_override,
        )
        yield (
            SSEEvent.terminal_success(
                draft_id=getattr(draft_obj, "id", None), success=True
            ).to_sse()
        )
