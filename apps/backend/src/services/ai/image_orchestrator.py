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
        # Provide a minimal staged Server-Sent Events generator for image
        # extraction so clients can monitor progress similar to URL
        # extraction. This is intentionally lightweight: the real
        # normalization/AI work currently happens synchronously in the POST
        # endpoint; this generator acts as a small replayer of stages and
        # verifies draft ownership when given a draft UUID as the
        # `source_url` parameter.
        from uuid import UUID

        from crud.ai_drafts import get_draft_by_id
        from schemas.ai import SSEEvent

        async def _gen() -> AsyncGenerator[str, None]:
            # Interpret source_url as draft id (UUID) for image streaming
            try:
                draft_uuid = UUID(str(source_url))
            except Exception:
                yield SSEEvent.terminal_error(
                    step="auth",
                    detail="Invalid draft id",
                    error_code="invalid_draft",
                ).to_sse()
                return

            # Fetch draft and verify ownership
            draft = await get_draft_by_id(db, draft_uuid, None)
            if not draft:
                yield SSEEvent.terminal_error(
                    step="fetch",
                    detail="Draft not found",
                    error_code="not_found",
                ).to_sse()
                return

            draft_user_raw = getattr(draft, "user_id", None)
            try:
                draft_user_uuid = UUID(str(draft_user_raw))
            except Exception:
                yield SSEEvent.terminal_error(
                    step="auth",
                    detail="Draft owner ID is invalid",
                    error_code="invalid_owner",
                ).to_sse()
                return

            if draft_user_uuid != current_user.id:
                yield SSEEvent.terminal_error(
                    step="auth",
                    detail="Draft does not belong to current user",
                    error_code="unauthorized",
                ).to_sse()
                return

            # Emit a small sequence of staged events. These are best-effort
            # progress markers and do not reflect live AI tokens.
            yield SSEEvent.model_validate(
                {"status": "started", "step": "started", "progress": 0.0}
            ).to_sse()

            yield SSEEvent.model_validate(
                {"status": "processing", "step": "normalize", "progress": 0.1}
            ).to_sse()

            yield SSEEvent.model_validate(
                {"status": "ai_call", "step": "ai_call", "progress": 0.5}
            ).to_sse()

            yield SSEEvent.model_validate(
                {"status": "converting", "step": "convert_schema", "progress": 0.75}
            ).to_sse()

            # Terminal event: success if payload exists on draft, failure otherwise
            success = bool(getattr(draft, "payload", None))
            yield (
                SSEEvent.terminal_success(
                    draft_id=str(draft_uuid), success=success
                ).to_sse()
            )

        return _gen()
