"""Image-specific orchestrator for recipe extraction from uploaded photos."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.observability import get_tracer, set_span_error_status
from models.users import User
from services.ai.extraction_common import DraftManager
from services.ai.interfaces import (
    AIAgentProtocol,
    AIExtractionService,
    RecipeConverterProtocol,
)
from services.ai.models import DraftOutcome


_tracer = get_tracer(__name__)


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
        with _tracer.start_as_current_span("ai_recipe_extract.image") as span:
            span.set_attribute("ai_recipe.source_type", "image")
            span.set_attribute("ai_recipe.streamed", False)
            span.set_attribute("ai_recipe.image_count", len(normalized_images))
            span.set_attribute(
                "ai_recipe.prompt_override_used", prompt_override is not None
            )
            try:
                try:
                    extraction_result = await self.ai_agent.run_image_extraction_agent(
                        normalized_images, prompt_override
                    )
                except Exception as e:
                    from schemas.ai import ExtractionNotFound

                    span.set_attribute("ai_recipe.extraction_status", "agent_error")
                    span.record_exception(e)
                    set_span_error_status(span, e)
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
                    span.set_attribute("ai_recipe.result_type", "failure_draft")
                    return DraftOutcome(
                        failure_draft, token, False, message="agent_error"
                    )

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
                    span.set_attribute("ai_recipe.extraction_status", "not_found")
                    span.set_attribute("ai_recipe.result_type", "failure_draft")
                    return DraftOutcome(
                        failure_draft, token, False, message="not_found"
                    )

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
                span.set_attribute("ai_recipe.extraction_status", "success")
                span.set_attribute("ai_recipe.result_type", "draft")
                return DraftOutcome(draft, token, True)
            except Exception as exc:
                span.set_attribute("ai_recipe.extraction_status", "error")
                span.record_exception(exc)
                set_span_error_status(span, exc)
                raise

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
        async def _gen() -> AsyncGenerator[str, None]:
            with _tracer.start_as_current_span(
                "ai_recipe_extract.image.stream"
            ) as span:
                span.set_attribute("ai_recipe.source_type", "image")
                span.set_attribute("ai_recipe.streamed", True)
                async for line in self._stream_image_progress(
                    source_url, db, current_user, span
                ):
                    yield line

        return _gen()

    async def _stream_image_progress(
        self,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        span: Any,
    ) -> AsyncGenerator[str, None]:
        from uuid import UUID

        from crud.ai_drafts import get_draft_by_id
        from schemas.ai import SSEEvent

        # Interpret source_url as draft id (UUID) for image streaming
        try:
            draft_uuid = UUID(str(source_url))
        except Exception:
            span.set_attribute("ai_recipe.extraction_status", "invalid_draft")
            yield SSEEvent.terminal_error(
                step="auth",
                detail="Invalid draft id",
                error_code="invalid_draft",
            ).to_sse()
            return

        # Fetch draft and verify ownership
        draft = await get_draft_by_id(db, draft_uuid, None)
        if not draft:
            span.set_attribute("ai_recipe.extraction_status", "not_found")
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
            span.set_attribute("ai_recipe.extraction_status", "invalid_owner")
            yield SSEEvent.terminal_error(
                step="auth",
                detail="Draft owner ID is invalid",
                error_code="invalid_owner",
            ).to_sse()
            return

        if draft_user_uuid != current_user.id:
            span.set_attribute("ai_recipe.extraction_status", "unauthorized")
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
        span.set_attribute(
            "ai_recipe.extraction_status", "success" if success else "not_found"
        )
        span.set_attribute(
            "ai_recipe.result_type", "draft" if success else "failure_draft"
        )
        yield (
            SSEEvent.terminal_success(
                draft_id=str(draft_uuid), success=success
            ).to_sse()
        )
