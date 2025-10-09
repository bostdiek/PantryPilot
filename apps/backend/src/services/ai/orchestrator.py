"""AI extraction orchestrator (Phase 1 refactor).

Simplified to remove legacy dynamic late-binding / importlib indirection.
All dependencies are explicit adapters around stable functions/classes:
* HTML: `HTMLExtractionService.fetch_and_sanitize`
* AI Agent: constructed via `create_recipe_agent`
* Recipe Conversion: `convert_to_recipe_create`
* Draft Operations: `draft_service` module functions

Tests should now inject alternative protocol implementations via FastAPI
dependency overrides instead of monkey-patching module symbols.
"""

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
from services.ai.html_extractor import HTMLExtractionService
from services.ai.interfaces import (
    AIAgentProtocol,
    AIExtractionService,
    DraftServiceProtocol,
    HTMLExtractorProtocol,
    RecipeConverterProtocol,
)
from services.ai.models import DraftOutcome


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
        self.html_extractor = html_extractor or HTMLExtractorAdapter()
        self.ai_agent = ai_agent or AIAgentAdapter()
        self.recipe_converter = recipe_converter or RecipeConverterAdapter()
        self.draft_service = draft_service or DraftServiceAdapter()

    async def extract_recipe_from_url(
        self,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> DraftOutcome[Any]:
        """Orchestrate a non-streaming extraction flow returning DraftOutcome."""
        # 1. Fetch + sanitize
        sanitized_html = await self.html_extractor.fetch_sanitized_html(source_url)
        if not sanitized_html:
            # Fetch failure -> synthesize not-found style failure draft for uniformity
            from schemas.ai import ExtractionNotFound  # noqa: PLC0415

            failure_draft = await self.draft_service.create_failure_draft(
                db=db,
                current_user=current_user,
                source_url=source_url,
                extraction_not_found=ExtractionNotFound(reason="fetch_failed"),
                prompt_override=prompt_override,
            )
            token = self.draft_service.create_draft_token(
                failure_draft.id, current_user.id, timedelta(hours=1)
            )
            return DraftOutcome(failure_draft, token, False, message="fetch_failed")

        # 2. Run AI agent
        extraction_result = await self.ai_agent.run_extraction_agent(
            sanitized_html, prompt_override
        )

        # Local import to avoid import cycles at module import time
        from schemas.ai import ExtractionNotFound  # noqa: PLC0415 (local import)

        if isinstance(extraction_result, ExtractionNotFound):
            failure_draft = await self.draft_service.create_failure_draft(
                db=db,
                current_user=current_user,
                source_url=source_url,
                extraction_not_found=extraction_result,
                prompt_override=prompt_override,
            )
            token = self.draft_service.create_draft_token(
                failure_draft.id, current_user.id, timedelta(hours=1)
            )
            return DraftOutcome(failure_draft, token, False, message="not_found")

        # 3. Convert to recipe create schema
        generated_recipe = self.recipe_converter.convert_to_recipe_create(
            extraction_result, source_url
        )

        # 4. Create success draft and token
        draft = await self.draft_service.create_success_draft(
            db=db,
            current_user=current_user,
            source_url=source_url,
            generated_recipe=generated_recipe,
            prompt_override=prompt_override,
        )
        token = self.draft_service.create_draft_token(
            draft.id, current_user.id, timedelta(hours=1)
        )
        return DraftOutcome(draft, token, True)

    async def extract_recipe_from_images(
        self,
        normalized_images: list[bytes],
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> DraftOutcome[Any]:
        """Orchestrate image-based extraction flow returning DraftOutcome.

        Args:
            normalized_images: List of normalized image bytes (JPEG format)
            db: Database session
            current_user: Authenticated user
            prompt_override: Optional custom prompt

        Returns:
            DraftOutcome containing draft, token, and success status
        """
        # 1. Create image recipe agent
        from services.ai.agents import create_image_recipe_agent

        agent = create_image_recipe_agent()

        # 2. Prepare multimodal messages with BinaryContent
        # Use pydantic-ai's BinaryContent for proper multimodal image handling
        from pydantic_ai.messages import BinaryContent

        prompt_text = prompt_override or (
            "Extract the complete recipe information from the provided image(s). "
            "Include all ingredients, instructions, times, and other details "
            "visible in the image."
        )

        # Build message list: prompt first, then BinaryContent for each image
        messages: list[str | BinaryContent] = [prompt_text]
        for img_bytes in normalized_images:
            messages.append(
                BinaryContent(data=img_bytes, media_type="image/jpeg")
            )

        # 3. Run AI agent with multimodal messages
        try:
            result = await agent.run(messages)
            extraction_result = getattr(result, "output", None) or getattr(
                result, "data", None
            )
        except Exception as e:
            # If agent fails, create a failure draft
            from schemas.ai import ExtractionNotFound

            extraction_not_found = ExtractionNotFound(
                reason=f"AI agent error: {str(e)}"
            )
            failure_draft = await self.draft_service.create_failure_draft(
                db=db,
                current_user=current_user,
                source_url="image_upload",
                extraction_not_found=extraction_not_found,
                prompt_override=prompt_override,
            )
            token = self.draft_service.create_draft_token(
                failure_draft.id, current_user.id, timedelta(hours=1)
            )
            return DraftOutcome(failure_draft, token, False, message="agent_error")

        # Local import to avoid import cycles at module import time
        from schemas.ai import ExtractionNotFound

        # 4. Check if extraction failed
        if isinstance(extraction_result, ExtractionNotFound):
            failure_draft = await self.draft_service.create_failure_draft(
                db=db,
                current_user=current_user,
                source_url="image_upload",
                extraction_not_found=extraction_result,
                prompt_override=prompt_override,
            )
            token = self.draft_service.create_draft_token(
                failure_draft.id, current_user.id, timedelta(hours=1)
            )
            return DraftOutcome(failure_draft, token, False, message="not_found")

        # 5. Convert to recipe create schema
        # Type guard: at this point extraction_result is RecipeExtractionResult
        from schemas.ai import RecipeExtractionResult

        if not isinstance(extraction_result, RecipeExtractionResult):
            # Unexpected result type, treat as failure
            extraction_not_found = ExtractionNotFound(
                reason="AI returned unexpected result type"
            )
            failure_draft = await self.draft_service.create_failure_draft(
                db=db,
                current_user=current_user,
                source_url="image_upload",
                extraction_not_found=extraction_not_found,
                prompt_override=prompt_override,
            )
            token = self.draft_service.create_draft_token(
                failure_draft.id, current_user.id, timedelta(hours=1)
            )
            return DraftOutcome(
                failure_draft, token, False, message="invalid_result_type"
            )

        generated_recipe = self.recipe_converter.convert_to_recipe_create(
            extraction_result, "image_upload"
        )

        # 6. Create success draft and token
        draft = await self.draft_service.create_success_draft(
            db=db,
            current_user=current_user,
            source_url="image_upload",
            generated_recipe=generated_recipe,
            prompt_override=prompt_override,
        )
        token = self.draft_service.create_draft_token(
            draft.id, current_user.id, timedelta(hours=1)
        )
        return DraftOutcome(draft, token, True)

    async def stream_extraction_progress(
        self,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream extraction progress as SSE-compatible strings.

        This method mirrors the prior streaming flow but uses injected protocol
        implementations rather than dynamic module resolution.
        """
        yield _line(
            SSEEvent.model_validate(
                {
                    "status": "started",
                    "step": "started",
                    "progress": 0.0,
                }
            )
        )
        yield _line(
            SSEEvent.model_validate(
                {"status": "fetching", "step": "fetch_html", "progress": 0.1}
            )
        )

        # Stage 1: fetch
        try:
            html = await self.html_extractor.fetch_sanitized_html(source_url)
        except Exception as e:
            yield _line(
                SSEEvent.terminal_error(
                    step="fetch_html",
                    detail=f"Fetch failed: {e}",
                    error_code="fetch_failed",
                )
            )
            return

        if not html:
            yield _line(
                SSEEvent.terminal_error(
                    step="fetch_html",
                    detail="No usable HTML content",
                    error_code="empty_html",
                )
            )
            return

        yield _line(
            SSEEvent.model_validate(
                {
                    "status": "sanitizing",
                    "step": "sanitize_html",
                    "progress": 0.25,
                }
            )
        )

        # Stage 2: agent
        yield _line(
            SSEEvent.model_validate(
                {"status": "ai_call", "step": "ai_call", "progress": 0.5}
            )
        )
        try:
            extraction_result = await self.ai_agent.run_extraction_agent(
                html, prompt_override
            )
        except Exception as e:
            yield _line(
                SSEEvent.terminal_error(
                    step="ai_call",
                    detail=f"AI agent failure: {e}",
                    error_code="agent_error",
                )
            )
            return

        # Local import to avoid import cycles at module import time
        from schemas.ai import ExtractionNotFound  # noqa: PLC0415 (local import)

        if isinstance(extraction_result, ExtractionNotFound):
            draft_obj = await self.draft_service.create_failure_draft(
                db, current_user, source_url, extraction_result, prompt_override
            )
            yield _line(
                SSEEvent.terminal_success(
                    draft_id=getattr(draft_obj, "id", None), success=False
                )
            )
            return

        # Stage 3: convert
        try:
            generated_recipe = self.recipe_converter.convert_to_recipe_create(
                extraction_result, source_url
            )
        except Exception as e:
            yield _line(
                SSEEvent.terminal_error(
                    step="convert_schema",
                    detail=f"Conversion failed: {e}",
                    error_code="convert_failed",
                )
            )
            return

        yield _line(
            SSEEvent.model_validate(
                {
                    "status": "converting",
                    "step": "convert_schema",
                    "progress": 0.75,
                }
            )
        )

        # Stage 4: success draft
        draft_obj = await self.draft_service.create_success_draft(
            db, current_user, source_url, generated_recipe, prompt_override
        )
        yield _line(
            SSEEvent.terminal_success(
                draft_id=getattr(draft_obj, "id", None), success=True
            )
        )


# FastAPI DI provider (used by API layer via Depends)
def get_ai_extraction_service() -> AIExtractionService:
    return Orchestrator()
