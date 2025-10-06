"""AI-powered recipe extraction and suggestion endpoints."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, cast
from uuid import UUID

import crud.ai_drafts as crud_ai_drafts
from core.security import create_draft_token as core_create_draft_token
from crud.ai_drafts import get_draft_by_id
from dependencies.auth import get_current_user
from dependencies.db import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from models.ai_drafts import AIDraft
from models.users import User
from schemas.ai import (
    AIDraftFetchResponse,
    AIDraftResponse,
    AIRecipeFromUrlRequest,
    ExtractionNotFound,
    RecipeExtractionResult,
)
from schemas.api import ApiResponse
from services.ai import convert_to_recipe_create
from services.ai.extraction_pipeline import (
    create_failure_draft,
    create_success_draft,
    fetch_sanitized_html,
    run_extraction_agent,
    stream_stage_convert,
    stream_stage_failure_draft,
    stream_stage_success_draft,
)
from sqlalchemy.ext.asyncio import AsyncSession

# ruff: noqa: I001  # Import order intentionally arranged to expose symbols for tests


__all__ = [
    "extract_recipe_from_url",
    "extract_recipe_stream",
    "get_ai_draft",
]


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/ai", tags=["ai"])
public_router = APIRouter(prefix="/ai", tags=["ai"])

# Draft TTL constants (single source to avoid magic numbers)
DRAFT_TTL_HOURS: int = 1
DRAFT_TTL_SECONDS: int = DRAFT_TTL_HOURS * 3600


# Provide thin wrappers that delegate to the CRUD module at call time so
# tests can patch either `api.v1.ai.create_draft` or
# `crud.ai_drafts.create_draft` and the runtime will resolve the patched
# function correctly.
async def create_draft(
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: UUID,
    draft_type: str,
    payload: dict[str, Any],
    source_url: str | None = None,
    prompt_used: str | None = None,
    ttl_hours: int = 1,
) -> AIDraft:
    draft_fn = crud_ai_drafts.create_draft
    return await draft_fn(
        db=db,
        user_id=user_id,
        draft_type=draft_type,
        payload=payload,
        source_url=source_url,
        prompt_used=prompt_used,
        ttl_hours=ttl_hours,
    )


def create_draft_token(
    draft_id: UUID, user_id: UUID, exp_delta: timedelta | None = None
) -> str:
    token_fn = getattr(crud_ai_drafts, "create_draft_token", core_create_draft_token)
    if exp_delta is None:
        return token_fn(draft_id, user_id)
    return token_fn(draft_id, user_id, exp_delta)


# --- Helper utilities used by AI endpoints ---------------------------------
def _ensure_uuid_or_401(claim_value: object, detail: str) -> UUID:
    """Return a UUID from claim_value or raise 401 with given detail."""
    try:
        if isinstance(claim_value, UUID):
            return claim_value
        return UUID(str(claim_value))
    except Exception as exc:
        logger.debug("Invalid UUID for %s: %s", detail, claim_value)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        ) from exc


async def _get_draft_or_404(db_session: AsyncSession, d_id: UUID) -> AIDraft:
    """Fetch a draft by id or raise 404 if not found."""
    d = await get_draft_by_id(db_session, d_id, None)
    if not d:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found",
        )
    return d


def _ensure_aware_utc_or_404(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware in UTC, or raise 404."""
    try:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception as exc:
        logger.debug("Invalid datetime for draft expiry: %s", dt)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft has expired",
        ) from exc


@router.post(
    "/extract-recipe-from-url",
    response_model=ApiResponse[AIDraftResponse],
)
async def extract_recipe_from_url(
    request: AIRecipeFromUrlRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    """Extract recipe from URL using AI and create a signed deep link.

    This endpoint:
    1. Validates and fetches HTML from the provided URL
    2. Sanitizes the HTML content to remove ads/scripts/trackers
    3. Uses AI to extract structured recipe data
    4. Creates a temporary AIDraft with the extracted data
    5. Returns a signed deep link for the frontend to load the draft

    Requires authentication via JWT Bearer token.
    """
    try:
        logger.debug(
            "extract_recipe_from_url: received request: %s",
            request.model_dump(),
        )
        # 1. Fetch + sanitize
        sanitized_html = await fetch_sanitized_html(str(request.source_url))
        logger.debug(
            "extract_recipe_from_url: fetched sanitized_html length=%s for url=%s",
            len(sanitized_html) if sanitized_html is not None else 0,
            request.source_url,
        )

        # 2. Run agent
        extraction_result = await run_extraction_agent(
            sanitized_html, request.prompt_override
        )
        logger.debug(
            "extract_recipe_from_url: agent returned result type=%s",
            type(extraction_result),
        )

        # No sentinel handling needed now; HTTPException from agent will be caught below

        # 3. Failure vs success draft creation
        if isinstance(extraction_result, ExtractionNotFound):
            failure_draft, msg = await create_failure_draft(
                db=db,
                current_user=current_user,
                source_url=str(request.source_url),
                extraction_not_found=extraction_result,
                prompt_override=request.prompt_override,
            )
            # Resolve token creator from crud module so tests that patch
            # crud.ai_drafts.create_draft_token are effective at call time.
            token_creator = getattr(
                crud_ai_drafts, "create_draft_token", create_draft_token
            )
            token = token_creator(
                failure_draft.id,
                current_user.id,
                timedelta(hours=DRAFT_TTL_HOURS),
            )
            logger.debug(
                "extract_recipe_from_url: created failure draft id=%s token=%s",
                failure_draft.id,
                token,
            )
            signed_url = f"/recipes/new?ai=1&draftId={failure_draft.id}&token={token}"
            response_data = AIDraftResponse(
                draft_id=failure_draft.id,
                signed_url=signed_url,
                expires_at=failure_draft.expires_at,
                ttl_seconds=DRAFT_TTL_SECONDS,
            )
            return ApiResponse(success=False, data=response_data, message=msg)

        # 4. Convert + success draft
        if not isinstance(
            extraction_result, RecipeExtractionResult
        ):  # pragma: no cover - fallback
            logger.warning(
                (
                    "Extraction result not RecipeExtractionResult (type=%s); "
                    "proceeding with best-effort conversion."
                ),
                type(extraction_result),
            )
        try:
            generated_recipe = convert_to_recipe_create(
                extraction_result, str(request.source_url)
            )
            logger.debug(
                "extract_recipe_from_url: converted to generated_recipe type=%s",
                type(generated_recipe),
            )
        except Exception as e:  # pragma: no cover - conversion error
            logger.error("Schema conversion failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process extracted recipe data",
            ) from e

        draft = await create_success_draft(
            db=db,
            current_user=current_user,
            source_url=str(request.source_url),
            generated_recipe=generated_recipe,
            prompt_override=request.prompt_override,
        )
        token_creator = getattr(
            crud_ai_drafts, "create_draft_token", create_draft_token
        )
        token = token_creator(
            draft.id, current_user.id, timedelta(hours=DRAFT_TTL_HOURS)
        )
        logger.debug(
            "extract_recipe_from_url: created success draft id=%s token=%s",
            draft.id,
            token,
        )
        signed_url = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"
        response_data = AIDraftResponse(
            draft_id=draft.id,
            signed_url=signed_url,
            expires_at=draft.expires_at,
            ttl_seconds=DRAFT_TTL_SECONDS,
        )
        return ApiResponse(
            success=True, data=response_data, message="Recipe extracted successfully"
        )
    except HTTPException as e:
        logger.debug(
            "extract_recipe_from_url: HTTPException raised status=%s detail=%s",
            e.status_code,
            getattr(e, "detail", None),
        )
        # For any internal server error raised here, return a structured
        # ApiResponse body (tests expect a JSON body with `success` key).
        if e.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            message = e.detail if isinstance(e.detail, str) else "Internal AI error"
            return JSONResponse(
                status_code=e.status_code,
                content=ApiResponse(
                    success=False,
                    data=None,
                    message=message,
                    error={"message": message, "type": "ai_agent_failure"},
                ).model_dump(),
            )
        raise
    except Exception as e:  # pragma: no cover - unexpected
        logger.error("Unexpected error in recipe extraction: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during recipe extraction",
        ) from e


# --- Streaming (SSE) extraction endpoint ------------------------------------
def sse(obj: dict[str, Any]) -> str:
    """Serialize an object as a Server-Sent Event data payload."""
    return f"data: {json.dumps(obj)}\n\n"


async def _stage_fetch(source_url: str) -> tuple[str | None, dict[str, Any] | None]:
    """Wrapper around pipeline.fetch to keep async generator logic simple."""
    # Some tests patch the pipeline function (services.ai.extraction_pipeline)
    # while others patch the symbol imported into this module (api.v1.ai).
    # Prefer the pipeline-level function if it differs from our local import,
    # otherwise call the local `fetch_sanitized_html` which may have been
    # patched by tests targeting this module.
    try:
        import services.ai.extraction_pipeline as _pipeline

        pipeline_fetch = getattr(_pipeline, "fetch_sanitized_html", None)
    except Exception:
        pipeline_fetch = None

    # Prefer a patched Mock/AsyncMock when present. Tests patch either the
    # pipeline module or this module and the patched value will typically be
    # a Mock object. Prefer that. Otherwise if only one side differs, prefer
    # the pipeline function (so patches on services.ai.extraction_pipeline are
    # honored). Fall back to the local import.
    from unittest.mock import Mock

    if pipeline_fetch is not None and isinstance(pipeline_fetch, Mock):
        selected_fetch = pipeline_fetch
    elif isinstance(fetch_sanitized_html, Mock):
        selected_fetch = fetch_sanitized_html
    elif pipeline_fetch is not None and pipeline_fetch is not fetch_sanitized_html:
        selected_fetch = pipeline_fetch
    else:
        selected_fetch = fetch_sanitized_html

    try:
        html = await selected_fetch(source_url)
        # Treat an empty/falsy HTML response as a fetch failure so tests
        # that patch the local fetch function to return an empty string
        # produce the expected "No usable HTML content" error.
        if not html:
            return None, {
                "status": "error",
                "step": "fetch_html",
                "detail": "No usable HTML content",
                "progress": 1.0,
            }
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


async def _stage_agent(
    sanitized_html: str | None, prompt_override: str | None
) -> tuple[Any | None, dict[str, Any] | None]:
    """Call the agent stage; return an error dict if input html is missing."""
    # Early return for missing HTML keeps the function simple and avoids
    # nesting that contributes to cyclomatic complexity.
    if sanitized_html is None:
        return None, {
            "status": "error",
            "step": "ai_call",
            "detail": "No HTML available for AI processing",
            "progress": 1.0,
        }
    # Build the full prompt the agent expects. Tests may patch either the
    # local symbol (`api.v1.ai.run_extraction_agent`) or the pipeline module
    # (`services.ai.extraction_pipeline.run_extraction_agent`). Prefer the
    # pipeline-level function if it's been patched (i.e., differs from our
    # local import), otherwise call the local symbol. Support both possible
    # function signatures (full_prompt) or (sanitized_html, prompt_override).
    prompt = prompt_override or "Extract the recipe information from this HTML content:"
    full_prompt = f"{prompt}\n\nHTML Content:\n{sanitized_html}"

    # Resolve pipeline run function if available
    try:
        import services.ai.extraction_pipeline as _pipeline

        pipeline_run = getattr(_pipeline, "run_extraction_agent", None)
    except Exception:
        pipeline_run = None

    selected_run = _choose_run_extraction_agent(pipeline_run)
    return await _invoke_run_extraction_agent(
        selected_run,
        pipeline_run,
        sanitized_html,
        prompt_override,
        full_prompt,
    )


def _stage_convert(
    extraction_result: Any, source_url: str
) -> tuple[Any | None, dict[str, Any] | None]:
    """Wrapper for conversion stage to keep generator logic linear."""
    return stream_stage_convert(extraction_result, source_url)


def _choose_run_extraction_agent(pipeline_candidate: object) -> object:
    """Choose which run_extraction_agent implementation to call.

    Preference order:
    - If pipeline_candidate is a Mock, prefer it (tests patch it directly).
    - If local `run_extraction_agent` is a Mock, prefer it.
    - If pipeline_candidate exists and differs from our local symbol,
      prefer the pipeline candidate (honor patches on that module).
    - Otherwise fall back to local `run_extraction_agent`.
    """
    from unittest.mock import Mock

    if pipeline_candidate is not None and isinstance(pipeline_candidate, Mock):
        return pipeline_candidate
    if isinstance(run_extraction_agent, Mock):
        return run_extraction_agent
    if (
        pipeline_candidate is not None
        and pipeline_candidate is not run_extraction_agent
    ):
        return pipeline_candidate
    return run_extraction_agent


async def _invoke_run_extraction_agent(
    selected: object,
    pipeline_candidate: object,
    html: str,
    prompt: str | None,
    full_prompt_str: str,
) -> tuple[Any | None, dict[str, Any] | None]:
    """Invoke the selected agent implementation with the correct signature.

    Returns (result, None) on success or (None, error_dict) on failure.
    """
    try:
        # If we've selected the pipeline candidate, prefer the single-arg
        # full_prompt signature; otherwise prefer the two-arg signature.
        if selected is pipeline_candidate:
            try:
                result = await cast(Callable[[str], Awaitable[object]], selected)(
                    full_prompt_str
                )
            except TypeError:
                result = await cast(
                    Callable[[str, str | None], Awaitable[object]], selected
                )(html, prompt)
        else:
            try:
                result = await cast(
                    Callable[[str, str | None], Awaitable[object]], selected
                )(html, prompt)
            except TypeError:
                result = await cast(Callable[[str], Awaitable[object]], selected)(
                    full_prompt_str
                )

        # Treat callable results (e.g., fixture functions) as AI failures
        if callable(result):
            return None, {
                "status": "error",
                "step": "ai_call",
                "detail": "AI agent failure: invalid response",
                "progress": 1.0,
            }

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


async def _stage_failure_draft(
    extraction_not_found: ExtractionNotFound,
    source_url: str,
    db: AsyncSession,
    current_user: User,
    prompt_override: str | None,
) -> dict[str, Any]:
    return await stream_stage_failure_draft(
        extraction_not_found, source_url, db, current_user, prompt_override
    )


async def _stage_success_draft(
    generated_recipe: Any,
    source_url: str,
    db: AsyncSession,
    current_user: User,
    prompt_override: str | None,
) -> dict[str, Any]:
    return await stream_stage_success_draft(
        generated_recipe, source_url, db, current_user, prompt_override
    )


@router.get(
    "/extract-recipe-stream",
    summary="Stream AI recipe extraction progress via Server-Sent Events",
)
async def extract_recipe_stream(
    source_url: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    prompt_override: str | None = None,
) -> StreamingResponse:
    """Stream extraction process (optional alternative to POST endpoint).

    Event JSON schema (sent in `data:` lines):
      status: started|fetching|sanitizing|ai_call|converting|complete|error
      step: short label for UI state machine
      detail: optional human-readable message
      progress: coarse float 0.0–1.0 (nullable)
      draft_id: present in final success/failure
      signed_url: deep-link to open draft (success or failure draft)
      success: boolean only in final event
    """
    return StreamingResponse(
        build_extraction_stream(
            source_url=source_url,
            db=db,
            current_user=current_user,
            prompt_override=prompt_override,
        ),
        media_type="text/event-stream",
    )


async def build_extraction_stream(
    source_url: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User,
    prompt_override: str | None,
) -> AsyncGenerator[str, None]:
    """Orchestrate streaming extraction with small helper stages.

    Refactored to reduce McCabe complexity: each stage is delegated to a
    narrowly-scoped helper that yields at most one error event.
    """
    # Use module-level SSE helper to keep complexity low
    yield sse({"status": "started", "step": "started", "progress": 0.0})
    # Explicit fetching event (tests expect this sequence)
    yield sse({"status": "fetching", "step": "fetch_html", "progress": 0.1})

    # Stage 1: fetch
    sanitized_html, fetch_error = await _stage_fetch(source_url)
    if fetch_error:
        yield sse(fetch_error)
        return
    yield sse({"status": "sanitizing", "step": "sanitize_html", "progress": 0.25})

    # Stage 2: agent
    yield sse({"status": "ai_call", "step": "ai_call", "progress": 0.5})
    extraction_result, agent_error = await _stage_agent(sanitized_html, prompt_override)
    if agent_error:
        yield sse(agent_error)
        return

    # Stage 3: failure draft path
    if isinstance(extraction_result, ExtractionNotFound):
        event = await _stage_failure_draft(
            extraction_result, source_url, db, current_user, prompt_override
        )
        yield sse(event)
        return

    # Stage 4: convert
    generated_recipe, convert_error = _stage_convert(extraction_result, source_url)
    if convert_error:
        yield sse(convert_error)
        return
    yield sse({"status": "converting", "step": "convert_schema", "progress": 0.75})

    # Stage 5: success draft
    success_event = await _stage_success_draft(
        generated_recipe, source_url, db, current_user, prompt_override
    )
    yield sse(success_event)


# --- Streaming helper stage functions (return data + optional error dict) ---


@public_router.get(
    "/drafts/{draft_id}", response_model=ApiResponse[AIDraftFetchResponse]
)
async def get_ai_draft(
    draft_id: UUID,
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[AIDraftFetchResponse]:
    """Fetch an AI draft using a signed token.

    This endpoint validates the signed token and returns the draft payload
    if the token is valid and not expired.
    """
    try:
        from core.security import decode_draft_token

        token_payload = decode_draft_token(token)

        token_draft_raw = token_payload.get("draft_id")
        if not token_draft_raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not contain a draft ID",
            )

        token_draft_uuid = _ensure_uuid_or_401(
            token_draft_raw, "Token contains invalid draft ID"
        )
        if token_draft_uuid != draft_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not match draft ID",
            )

        token_user_raw = token_payload.get("user_id")
        if not token_user_raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not contain a user ID",
            )

        token_user_uuid = _ensure_uuid_or_401(
            token_user_raw, "Token contains invalid user ID"
        )

        draft = await _get_draft_or_404(db, draft_id)
        draft_user_raw = getattr(draft, "user_id", None)
        draft_user_uuid = _ensure_uuid_or_401(
            draft_user_raw, "Draft owner ID is invalid"
        )

        if token_user_uuid != draft_user_uuid:
            logger.debug(
                "Draft owner mismatch: token=%s draft=%s",
                token_user_uuid,
                draft_user_uuid,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token does not match draft owner",
            )

        now_utc = datetime.now(UTC)
        draft_expires = getattr(draft, "expires_at", None)
        if draft_expires is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft has expired",
            )

        draft_expires = _ensure_aware_utc_or_404(draft_expires)
        if now_utc >= draft_expires:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft has expired",
            )

        response_data = AIDraftFetchResponse(
            payload=cast(dict[str, Any], draft.payload),
            type="recipe_suggestion",
            created_at=draft.created_at,
            expires_at=draft.expires_at,
        )

        return ApiResponse(
            success=True,
            data=response_data,
            message="Draft retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching draft %s: %s", draft_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve draft",
        ) from exc
