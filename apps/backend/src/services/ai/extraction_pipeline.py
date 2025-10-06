"""Shared AI recipe extraction helpers and streaming stage functions.

This module centralizes the orchestration primitives used by both the POST
extraction endpoint and the Server-Sent Events (SSE) streaming endpoint so
the API router file stays lean and readable.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from pydantic_ai import AgentRunError
from sqlalchemy.ext.asyncio import AsyncSession

import crud.ai_drafts as crud_ai_drafts
from core.security import create_draft_token
from models.ai_drafts import AIDraft
from models.users import User
from schemas.ai import (
    ExtractionFailureResponse,
    ExtractionNotFound,
    RecipeExtractionResult,
)
from services.ai import (
    HTMLExtractionService,
    convert_to_recipe_create,
    create_recipe_agent,
)


__all__ = [
    "fetch_sanitized_html",
    "run_extraction_agent",
    "create_failure_draft",
    "create_success_draft",
    "stream_stage_fetch",
    "stream_stage_agent",
    "stream_stage_failure_draft",
    "stream_stage_convert",
    "stream_stage_success_draft",
]


# Single shared instance (stateless aside from network I/O)
_html_service = HTMLExtractionService()

# Draft TTL constant (kept in sync with api.v1.ai)
DRAFT_TTL_HOURS = 1


async def fetch_sanitized_html(source_url: str) -> str:
    """Fetch and sanitize HTML or raise HTTPException with appropriate status."""
    sanitized_html = await _html_service.fetch_and_sanitize(str(source_url))
    if not sanitized_html:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No usable content found at the provided URL",
        )
    return sanitized_html


async def run_extraction_agent(sanitized_html: str, prompt_override: str | None) -> Any:
    """Run the AI extraction agent and return its pydantic output object.

    Normalizes result attribute differences (``output`` vs ``data``) and raises
    HTTPException for any agent failures so callers can rely on exceptions.
    """
    # Support test patching via api.v1.ai.create_recipe_agent; fallback to local import
    try:  # pragma: no cover - dynamic override path
        from api.v1 import ai as ai_module

        agent_factory = getattr(ai_module, "create_recipe_agent", create_recipe_agent)
    except Exception:  # pragma: no cover - fallback
        agent_factory = create_recipe_agent
    agent = agent_factory()
    prompt = prompt_override or "Extract the recipe information from this HTML content:"
    full_prompt = f"{prompt}\n\nHTML Content:\n{sanitized_html}"
    try:
        result: Any = await agent.run(full_prompt)
    except AgentRunError as e:  # model/tooling failure
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Failed to extract recipe using AI. The content may not "
                "contain a valid recipe."
            ),
        ) from e
    except Exception as e:  # pragma: no cover - unexpected agent error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI processing failed",
        ) from e

    extraction_result = getattr(result, "output", None) or getattr(result, "data", None)
    if extraction_result is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI extraction result is empty",
        )
    return extraction_result


async def create_failure_draft(
    *,
    db: AsyncSession,
    current_user: User,
    source_url: str,
    extraction_not_found: ExtractionNotFound,
    prompt_override: str | None,
) -> tuple[AIDraft, str]:
    """Persist and return a failure draft and user-facing message."""
    failure = ExtractionFailureResponse(
        reason=extraction_not_found.reason,
        source_url=str(source_url),
        details={"note": "No recipe found on page"},
    )
    payload: dict[str, Any] = {
        "generated_recipe": None,
        "extraction_metadata": {
            "failure": failure.model_dump(),
            "source_url": str(source_url),
            "extracted_at": datetime.now(UTC).isoformat(),
        },
    }
    # Allow tests to patch api.v1.ai.create_draft or crud.ai_drafts.create_draft;
    # prefer an override on the api module if present, otherwise call the
    # current attribute on the crud.ai_drafts module so tests that patch
    # that module are honored at call time.
    try:  # pragma: no cover - dynamic override path
        from api.v1 import ai as ai_module

        ai_create = getattr(ai_module, "create_draft", None)
    except Exception:  # pragma: no cover - fallback
        ai_create = None

    # Prefer api-level override if provided, otherwise call the CRUD
    # implementation directly (the CRUD module can be patched by tests).
    if ai_create is not None:
        draft: AIDraft = await ai_create(
            db=db,
            user_id=current_user.id,
            draft_type="recipe_suggestion",
            payload=payload,
            source_url=str(source_url),
            prompt_used=prompt_override,
            ttl_hours=DRAFT_TTL_HOURS,
        )
    else:
        draft = await crud_ai_drafts.create_draft(
            db=db,
            user_id=current_user.id,
            draft_type="recipe_suggestion",
            payload=payload,
            source_url=str(source_url),
            prompt_used=prompt_override,
            ttl_hours=DRAFT_TTL_HOURS,
        )
    return draft, f"Recipe extraction failed: {failure.reason}"


async def create_success_draft(
    *,
    db: AsyncSession,
    current_user: User,
    source_url: str,
    generated_recipe: Any,
    prompt_override: str | None,
) -> AIDraft:
    """Persist and return a successful extraction draft."""
    meta: dict[str, Any] = {
        "confidence_score": float(getattr(generated_recipe, "confidence_score", 0.0)),
        "source_url": str(source_url),
        "extracted_at": datetime.now(UTC).isoformat(),
    }
    payload: dict[str, Any] = {
        "generated_recipe": generated_recipe.model_dump(),
        "extraction_metadata": meta,
    }
    try:  # pragma: no cover - dynamic override path
        from api.v1 import ai as ai_module

        ai_create = getattr(ai_module, "create_draft", None)
    except Exception:  # pragma: no cover - fallback
        ai_create = None

    if ai_create is not None:
        draft: AIDraft = await ai_create(
            db=db,
            user_id=current_user.id,
            draft_type="recipe_suggestion",
            payload=payload,
            source_url=str(source_url),
            prompt_used=prompt_override,
            ttl_hours=DRAFT_TTL_HOURS,
        )
    else:
        draft = await crud_ai_drafts.create_draft(
            db=db,
            user_id=current_user.id,
            draft_type="recipe_suggestion",
            payload=payload,
            source_url=str(source_url),
            prompt_used=prompt_override,
            ttl_hours=DRAFT_TTL_HOURS,
        )
    return draft


# --------------------- Streaming stage helper functions ---------------------


async def stream_stage_fetch(
    source_url: str,
) -> tuple[str | None, dict[str, Any] | None]:
    try:
        html = await fetch_sanitized_html(source_url)
        return html, None
    except HTTPException as e:  # expected fetch/sanitize problems
        detail = getattr(e, "detail", str(e))
        if "No usable content" in str(detail):
            final_detail = "No usable HTML content"
        else:
            final_detail = f"Fetch failed: {detail}"
        return None, {
            "status": "error",
            "step": "fetch_html",
            "detail": final_detail,
            "progress": 1.0,
        }
    except Exception as e:  # pragma: no cover - defensive
        return None, {
            "status": "error",
            "step": "fetch_html",
            "detail": f"Fetch failed: {e}",
            "progress": 1.0,
        }


async def stream_stage_agent(
    sanitized_html: str, prompt_override: str | None
) -> tuple[Any | None, dict[str, Any] | None]:
    try:
        result = await run_extraction_agent(sanitized_html, prompt_override)
        return result, None
    except HTTPException as e:
        detail = getattr(e, "detail", str(e))
        return None, {
            "status": "error",
            "step": "ai_call",
            "detail": f"AI agent failure: {detail}",
            "progress": 1.0,
        }
    except Exception as e:  # pragma: no cover - defensive
        return None, {
            "status": "error",
            "step": "ai_call",
            "detail": f"Unexpected AI error: {e}",
            "progress": 1.0,
        }


async def stream_stage_failure_draft(
    extraction_not_found: ExtractionNotFound,
    source_url: str,
    db: AsyncSession,
    current_user: User,
    prompt_override: str | None,
) -> dict[str, Any]:
    try:
        draft, msg = await create_failure_draft(
            db=db,
            current_user=current_user,
            source_url=source_url,
            extraction_not_found=extraction_not_found,
            prompt_override=prompt_override,
        )
        token = create_draft_token(
            draft.id, current_user.id, timedelta(hours=DRAFT_TTL_HOURS)
        )
        signed_url = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"
        return {
            "status": "complete",
            "step": "complete",
            "detail": msg,
            "progress": 1.0,
            "draft_id": str(draft.id),
            "signed_url": signed_url,
            "success": False,
        }
    except Exception as e:  # pragma: no cover - persistence error
        return {
            "status": "error",
            "step": "persist_failure_draft",
            "detail": f"Failed to persist failure draft: {e}",
            "progress": 1.0,
        }


def stream_stage_convert(
    extraction_result: Any, source_url: str
) -> tuple[Any | None, dict[str, Any] | None]:
    try:
        if not isinstance(
            extraction_result, RecipeExtractionResult
        ):  # pragma: no cover
            raise ValueError("Unexpected extraction result type")
        recipe = convert_to_recipe_create(extraction_result, source_url)
        return recipe, None
    except Exception as e:
        return None, {
            "status": "error",
            "step": "convert_schema",
            "detail": f"Conversion failed: {e}",
            "progress": 1.0,
        }


async def stream_stage_success_draft(
    generated_recipe: Any,
    source_url: str,
    db: AsyncSession,
    current_user: User,
    prompt_override: str | None,
) -> dict[str, Any]:
    try:
        draft = await create_success_draft(
            db=db,
            current_user=current_user,
            source_url=source_url,
            generated_recipe=generated_recipe,
            prompt_override=prompt_override,
        )
        token = create_draft_token(
            draft.id, current_user.id, timedelta(hours=DRAFT_TTL_HOURS)
        )
        signed_url = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"
        confidence_score = float(getattr(generated_recipe, "confidence_score", 0.0))
        return {
            "status": "complete",
            "step": "complete",
            "detail": "Recipe extracted successfully",
            "progress": 1.0,
            "draft_id": str(draft.id),
            "signed_url": signed_url,
            "success": True,
            "confidence_score": confidence_score,
        }
    except Exception as e:  # pragma: no cover - persistence error
        return {
            "status": "error",
            "step": "persist_draft",
            "detail": f"Failed to persist draft: {e}",
            "progress": 1.0,
        }
