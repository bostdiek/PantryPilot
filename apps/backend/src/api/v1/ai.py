"""AI-powered recipe extraction and suggestion endpoints."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic_ai import AgentRunError
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_draft_token
from crud.ai_drafts import create_draft, get_draft_by_id
from dependencies.auth import get_current_user
from dependencies.db import get_db
from models.ai_drafts import AIDraft
from models.users import User
from schemas.ai import (
    AIDraftFetchResponse,
    AIDraftResponse,
    AIRecipeFromUrlRequest,
    ExtractionFailureResponse,
    ExtractionNotFound,
    RecipeExtractionResult,
)
from schemas.api import ApiResponse, ErrorResponse
from services.ai import (
    HTMLExtractionService,
    convert_to_recipe_create,
    create_recipe_agent,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])
public_router = APIRouter(prefix="/ai", tags=["ai"])

# Initialize services
html_service = HTMLExtractionService()

# Draft TTL constants (single source to avoid magic numbers)
DRAFT_TTL_HOURS: int = 1
DRAFT_TTL_SECONDS: int = DRAFT_TTL_HOURS * 3600


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
async def extract_recipe_from_url(  # noqa: C901 - endpoint orchestration
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
        # Step 1: Fetch and sanitize HTML
        logger.info(f"Fetching recipe from URL: {request.source_url}")
        sanitized_html = await html_service.fetch_and_sanitize(str(request.source_url))
        if not sanitized_html:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No usable content found at the provided URL",
            )

        # Step 2: Create AI agent and extract recipe
        logger.info("Extracting recipe using AI agent")
        agent = create_recipe_agent()

        prompt = (
            request.prompt_override
            or "Extract the recipe information from this HTML content:"
        )
        full_prompt = f"{prompt}\n\nHTML Content:\n{sanitized_html}"

        try:
            result: Any = await agent.run(full_prompt)
            # Primary attribute (newer pydantic_ai) is `output`; retain
            # backward compatibility with earlier test/mocks using `data`.
            extraction_result = getattr(result, "output", None)
            if extraction_result is None:
                extraction_result = getattr(result, "data", None)

            # If the agent explicitly returned the failure output, handle it
            if isinstance(extraction_result, ExtractionNotFound):
                logger.info("AI agent reported no extractable recipe found")
                failure = ExtractionFailureResponse(
                    reason=extraction_result.reason,
                    source_url=str(request.source_url),
                    details={"note": "No recipe found on page"},
                )

                # Store failure in draft payload so frontend can inspect it
                failure_payload: dict[str, Any] = {
                    "generated_recipe": None,
                    "extraction_metadata": {
                        "failure": failure.model_dump(),
                        "source_url": str(request.source_url),
                        "extracted_at": datetime.now(UTC).isoformat(),
                    },
                }

                failure_draft: AIDraft = await create_draft(
                    db=db,
                    user_id=current_user.id,
                    draft_type="recipe_suggestion",
                    payload=failure_payload,
                    source_url=str(request.source_url),
                    prompt_used=request.prompt_override,
                    ttl_hours=DRAFT_TTL_HOURS,
                )

                ttl = timedelta(hours=DRAFT_TTL_HOURS)
                token = create_draft_token(failure_draft.id, current_user.id, ttl)
                signed_url = (
                    f"/recipes/new?ai=1&draftId={failure_draft.id}&token={token}"
                )

                response_data = AIDraftResponse(
                    draft_id=failure_draft.id,
                    signed_url=signed_url,
                    expires_at=failure_draft.expires_at,
                    ttl_seconds=DRAFT_TTL_SECONDS,
                )

                return ApiResponse(
                    success=False,
                    data=response_data,
                    message=(f"Recipe extraction failed: {failure.reason}"),
                )

            logger.info(
                "AI extraction completed with confidence: %s",
                getattr(extraction_result, "confidence_score", None),
            )

        except AgentRunError as e:
            logger.error(f"AI agent failed: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=ErrorResponse(
                    message=(
                        "Failed to extract recipe using AI. The content may not "
                        "contain a valid recipe."
                    ),
                    error={"message": str(e), "type": "ai_agent_failure"},
                ).model_dump(),
            )
        except Exception as e:
            logger.error(f"Unexpected AI error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI processing failed",
            ) from e

        # Step 3: Convert to standard recipe schema
        try:
            # Prefer proper type but fall back for legacy mocks (tests) where
            # a plain object or mock is provided. Only hard-fail if None.
            if extraction_result is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="AI extraction result is empty",
                )
            if not isinstance(
                extraction_result, RecipeExtractionResult
            ):  # pragma: no cover - log fallback
                logger.warning(
                    (
                        "Extraction result not RecipeExtractionResult (type=%s); "
                        "proceeding with best-effort conversion."
                    ),
                    type(extraction_result),
                )
            generated_recipe = convert_to_recipe_create(
                extraction_result, str(request.source_url)
            )
        except Exception as e:
            logger.error(f"Schema conversion failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process extracted recipe data",
            ) from e

        # Step 4: Create draft with extracted data
        extraction_metadata: dict[str, Any] = {
            "confidence_score": float(
                getattr(generated_recipe, "confidence_score", 0.0)
            ),
            "source_url": str(request.source_url),
            "extracted_at": datetime.now(UTC).isoformat(),
        }

        draft_payload: dict[str, Any] = {
            "generated_recipe": generated_recipe.model_dump(),
            "extraction_metadata": extraction_metadata,
        }

        draft: AIDraft = await create_draft(
            db=db,
            user_id=current_user.id,
            draft_type="recipe_suggestion",
            payload=draft_payload,
            source_url=str(request.source_url),
            prompt_used=request.prompt_override,
            ttl_hours=DRAFT_TTL_HOURS,
        )

        # Step 5: Create signed token and deep link
        ttl = timedelta(hours=DRAFT_TTL_HOURS)
        token = create_draft_token(draft.id, current_user.id, ttl)
        signed_url = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"

        response_data = AIDraftResponse(
            draft_id=draft.id,
            signed_url=signed_url,
            expires_at=draft.expires_at,
            ttl_seconds=DRAFT_TTL_SECONDS,
        )

        logger.info(
            f"Successfully created AI draft {draft.id} for user {current_user.id}"
        )

        return ApiResponse(
            success=True, data=response_data, message="Recipe extracted successfully"
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in recipe extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during recipe extraction",
        ) from e


# --- Streaming (SSE) extraction endpoint ------------------------------------
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


async def build_extraction_stream(  # noqa: C901 - generator with multiple stages
    source_url: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User,
    prompt_override: str | None,
) -> AsyncGenerator[str, None]:
    agent = create_recipe_agent()

    def sse(obj: dict[str, Any]) -> str:
        return f"data: {json.dumps(obj)}\n\n"

    # started
    yield sse({"status": "started", "step": "started", "progress": 0.0})

    # fetch
    yield sse({"status": "fetching", "step": "fetch_html", "progress": 0.1})
    try:
        sanitized_html = await html_service.fetch_and_sanitize(str(source_url))
    except Exception as e:  # network or parsing error
        yield sse(
            {
                "status": "error",
                "step": "fetch_html",
                "detail": f"Fetch failed: {e}",
                "progress": 1.0,
            }
        )
        return

    if not sanitized_html:
        yield sse(
            {
                "status": "error",
                "step": "fetch_html",
                "detail": "No usable HTML content",
                "progress": 1.0,
            }
        )
        return

    yield sse({"status": "sanitizing", "step": "sanitize_html", "progress": 0.25})

    # AI call
    prompt = prompt_override or "Extract the recipe information from this HTML content:"
    full_prompt = f"{prompt}\n\nHTML Content:\n{sanitized_html}"
    yield sse({"status": "ai_call", "step": "call_model", "progress": 0.55})
    try:
        result: Any = await agent.run(full_prompt)
        extraction_result = getattr(result, "output", None)
        if extraction_result is None:
            extraction_result = getattr(result, "data", None)
    except AgentRunError as e:
        yield sse(
            {
                "status": "error",
                "step": "ai_call",
                "detail": f"AI agent failure: {e}",
                "progress": 1.0,
            }
        )
        return
    except Exception as e:
        yield sse(
            {
                "status": "error",
                "step": "ai_call",
                "detail": f"Unexpected AI error: {e}",
                "progress": 1.0,
            }
        )
        return

    # Not found case
    if isinstance(extraction_result, ExtractionNotFound):
        try:
            failure = ExtractionFailureResponse(
                reason=extraction_result.reason,
                source_url=str(source_url),
                details={"note": "No recipe found on page"},
            )
            failure_payload: dict[str, Any] = {
                "generated_recipe": None,
                "extraction_metadata": {
                    "failure": failure.model_dump(),
                    "source_url": str(source_url),
                    "extracted_at": datetime.now(UTC).isoformat(),
                },
            }
            failure_draft: AIDraft = await create_draft(
                db=db,
                user_id=current_user.id,
                draft_type="recipe_suggestion",
                payload=failure_payload,
                source_url=str(source_url),
                prompt_used=prompt_override,
                ttl_hours=DRAFT_TTL_HOURS,
            )
            token = create_draft_token(
                failure_draft.id, current_user.id, timedelta(hours=DRAFT_TTL_HOURS)
            )
            signed_url = f"/recipes/new?ai=1&draftId={failure_draft.id}&token={token}"
            yield sse(
                {
                    "status": "complete",
                    "step": "complete",
                    "detail": f"Recipe extraction failed: {failure.reason}",
                    "progress": 1.0,
                    "draft_id": str(failure_draft.id),
                    "signed_url": signed_url,
                    "success": False,
                }
            )
        except Exception as e:
            yield sse(
                {
                    "status": "error",
                    "step": "persist_failure_draft",
                    "detail": f"Failed to persist failure draft: {e}",
                    "progress": 1.0,
                }
            )
        return

    # Convert
    yield sse({"status": "converting", "step": "convert_schema", "progress": 0.75})
    try:
        if not isinstance(extraction_result, RecipeExtractionResult):
            raise ValueError("Unexpected extraction result type")
        generated_recipe = convert_to_recipe_create(extraction_result, str(source_url))
    except Exception as e:
        yield sse(
            {
                "status": "error",
                "step": "convert_schema",
                "detail": f"Conversion failed: {e}",
                "progress": 1.0,
            }
        )
        return

    # Persist success draft
    try:
        extraction_metadata: dict[str, Any] = {
            "confidence_score": float(
                getattr(generated_recipe, "confidence_score", 0.0)
            ),
            "source_url": str(source_url),
            "extracted_at": datetime.now(UTC).isoformat(),
        }
        draft_payload: dict[str, Any] = {
            "generated_recipe": generated_recipe.model_dump(),
            "extraction_metadata": extraction_metadata,
        }
        draft: AIDraft = await create_draft(
            db=db,
            user_id=current_user.id,
            draft_type="recipe_suggestion",
            payload=draft_payload,
            source_url=str(source_url),
            prompt_used=prompt_override,
            ttl_hours=DRAFT_TTL_HOURS,
        )
        token = create_draft_token(
            draft.id, current_user.id, timedelta(hours=DRAFT_TTL_HOURS)
        )
        signed_url = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"
        yield sse(
            {
                "status": "complete",
                "step": "complete",
                "detail": "Recipe extracted successfully",
                "progress": 1.0,
                "draft_id": str(draft.id),
                "signed_url": signed_url,
                "success": True,
                "confidence_score": extraction_metadata["confidence_score"],
            }
        )
    except Exception as e:
        yield sse(
            {
                "status": "error",
                "step": "persist_draft",
                "detail": f"Failed to persist draft: {e}",
                "progress": 1.0,
            }
        )
        return


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
