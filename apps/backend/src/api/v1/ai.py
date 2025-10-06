"""AI-powered recipe extraction and suggestion endpoints.

Phase 1 Refactor:
Removed legacy thin wrapper functions (`fetch_sanitized_html`, `run_extraction_agent`,
`convert_to_recipe_create`, draft/token helpers, and streaming stage adapters) that
previously proxied to service/orchestrator internals for test patching. Tests will
now override the FastAPI dependency `get_ai_extraction_service` directly instead
of monkey-patching module-level symbols. This keeps the API layer slim and focused
only on request validation, calling the orchestrator service, and shaping responses.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from crud.ai_drafts import get_draft_by_id
from dependencies.auth import get_current_user
from dependencies.db import get_db
from models.ai_drafts import AIDraft
from models.users import User
from schemas.ai import AIDraftFetchResponse, AIDraftResponse, AIRecipeFromUrlRequest
from schemas.api import ApiResponse
from services.ai.interfaces import AIExtractionService
from services.ai.models import DraftOutcome
from services.ai.orchestrator import get_ai_extraction_service


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/ai", tags=["ai"])
public_router = APIRouter(prefix="/ai", tags=["ai"])

# Draft TTL constants (single source to avoid magic numbers)
DRAFT_TTL_HOURS: int = 1
DRAFT_TTL_SECONDS: int = DRAFT_TTL_HOURS * 3600


## Legacy wrappers removed: tests should now inject fakes via dependency overrides.


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
    ai_service: Annotated[AIExtractionService, Depends(get_ai_extraction_service)],
) -> Any:
    """Extract recipe from URL using injected service and return signed deep link.

    Delegates orchestration to the injected service (no module-level wrappers).
    """
    try:
        logger.debug(
            "extract_recipe_from_url: received request: %s",
            request.model_dump(),
        )

        outcome: DraftOutcome[AIDraft] = await ai_service.extract_recipe_from_url(
            str(request.source_url), db, current_user, request.prompt_override
        )
        draft, token, success = outcome.draft, outcome.token, outcome.success

        signed_url = f"/recipes/new?ai=1&draftId={draft.id}&token={token}"
        # Ensure expires_at is a timezone-aware datetime for the response model
        expires = getattr(draft, "expires_at", None)
        if expires is None:
            # If draft has no expiry, treat as expired for safety
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft has expired",
            )
        expires_dt = _ensure_aware_utc_or_404(expires)

        response_data = AIDraftResponse(
            draft_id=draft.id,
            signed_url=signed_url,
            expires_at=expires_dt,
            ttl_seconds=DRAFT_TTL_SECONDS,
        )
        return ApiResponse(
            success=bool(success),
            data=response_data,
            message="Recipe extracted successfully" if success else "Recipe not found",
        )
    except HTTPException as e:
        logger.debug(
            "extract_recipe_from_url: HTTPException raised status=%s detail=%s",
            e.status_code,
            getattr(e, "detail", None),
        )
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


# Legacy streaming stage helpers removed; orchestrator now encapsulates all stages.


@router.get(
    "/extract-recipe-stream",
    summary="Stream AI recipe extraction progress via Server-Sent Events",
)
async def extract_recipe_stream(
    source_url: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    ai_service: Annotated[AIExtractionService, Depends(get_ai_extraction_service)],
    prompt_override: str | None = None,
) -> StreamingResponse:
    """Stream extraction process by delegating to the injected orchestrator service."""
    # ai_service.stream_extraction_progress returns an AsyncGenerator[str, None]
    # which is acceptable to StreamingResponse as an async iterable.
    return StreamingResponse(
        ai_service.stream_extraction_progress(
            source_url, db, current_user, prompt_override
        ),
        media_type="text/event-stream",
    )


# build_extraction_stream removed. Streaming delegated to injected service via
# `extract_recipe_stream` calling orchestrator's `stream_extraction_progress`.


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
