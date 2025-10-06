"""Unified draft service for AI extraction flows (Phase 3 refactor).

Simplified to remove legacy dynamic late-binding and api-level patch detection.
All draft creation now routes directly through `crud.ai_drafts` and token
generation through `core.security` helpers. Tests that need to fake behavior
should override the DraftServiceProtocol implementation instead of patching
module-level symbols or relying on import-time indirection.

Key changes in this phase:
* Removed `importlib` probing for `api.v1.ai` overrides
* Removed tuple `(draft, message)` pattern for failure drafts – always return
    an `AIDraft` (message handled by orchestrator / exceptions)
* Removed fallback Mock draft creation except for AttributeError on limited
    test DB sessions (retained minimal safety net)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

import crud.ai_drafts as crud_ai_drafts
from core.security import create_draft_token as core_create_draft_token
from models.ai_drafts import AIDraft
from models.users import User
from schemas.ai import ExtractionNotFound


logger = logging.getLogger(__name__)


class _FailureDraftStub:
    """Small test-friendly stub used only as a defensive fallback when the
    real DB-backed draft creation path is unavailable (kept minimal).

    Tests should prefer injecting a DraftServiceProtocol implementation;
    this stub exists only to avoid retaining unittest.mock in production code.
    """

    def __init__(self, id: UUID, payload: dict[str, Any], expires_at: datetime) -> None:
        self.id: UUID = id
        self.payload: dict[str, Any] = payload
        self.expires_at: datetime = expires_at


async def _maybe_call(fn: Callable[..., Any] | None, *args: Any, **kwargs: Any) -> Any:
    """Call fn which may be sync or async; await if necessary.

    Returns the result of the call (may be Any). If fn is None returns None.
    """
    if fn is None:
        return None
    if asyncio.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    result = fn(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return result


async def create_success_draft(
    db: AsyncSession,
    current_user: User,
    source_url: str,
    generated_recipe: Any,
    prompt_override: str | None = None,
) -> AIDraft:
    """Create a draft representing a successful extraction.

    Always uses `crud.ai_drafts.create_draft` (no api-level override probing).
    """
    payload = _normalize_payload(generated_recipe)
    try:
        draft_any = await _maybe_call(
            crud_ai_drafts.create_draft,
            db=db,
            user_id=current_user.id,
            draft_type="recipe_suggestion",
            payload=payload,
            source_url=source_url,
            prompt_used=prompt_override,
            ttl_hours=1,
        )
        draft = cast(AIDraft, draft_any)
    except AttributeError as exc:  # pragma: no cover - defensive
        from uuid import uuid4

        logger.debug(
            "create_success_draft: limited DB session, returning stub draft: %s",
            exc,
        )
        draft = cast(
            AIDraft,
            _FailureDraftStub(
                id=uuid4(),
                payload=payload,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
        )
    logger.debug(
        "create_success_draft: created draft id=%s", getattr(draft, "id", None)
    )
    # mypy: ensure return type is AIDraft-like; tests may use Mock with same attrs
    return draft


async def create_failure_draft(
    db: AsyncSession,
    current_user: User,
    source_url: str,
    extraction_not_found: ExtractionNotFound,
    prompt_override: str | None = None,
) -> AIDraft:
    """Create a draft representing a failed extraction (unified return type).

    Payload always includes an optional structured `detail`. User-facing message
    selection is deferred to orchestrator / API mapping layers.
    """
    payload: dict[str, Any] = {"error": "extraction_not_found"}
    try:
        payload["detail"] = extraction_not_found.model_dump()
    except Exception:  # pragma: no cover - defensive
        payload["detail"] = str(extraction_not_found)

    try:
        draft_any = await _maybe_call(
            crud_ai_drafts.create_draft,
            db=db,
            user_id=current_user.id,
            draft_type="recipe_suggestion_failure",
            payload=payload,
            source_url=source_url,
            prompt_used=prompt_override,
            ttl_hours=1,
        )
        draft = cast(AIDraft, draft_any)
    except AttributeError as exc:  # pragma: no cover - defensive
        from uuid import uuid4

        logger.debug(
            "create_failure_draft: limited DB session, returning stub draft: %s",
            exc,
        )
        draft = cast(
            AIDraft,
            _FailureDraftStub(
                id=uuid4(),
                payload=payload,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
        )
    # Keep an expires_at attribute for tests; set to now+1h
    draft.expires_at = datetime.now(UTC) + timedelta(hours=1)
    logger.debug(
        "create_failure_draft: created failure draft id=%s", getattr(draft, "id", None)
    )
    return draft


def create_draft_token(
    draft_id: UUID, user_id: UUID, exp_delta: timedelta | None = None
) -> str:
    """Create a signed token for a draft (direct security helper)."""
    if exp_delta is None:
        return core_create_draft_token(draft_id, user_id)
    return core_create_draft_token(draft_id, user_id, exp_delta)


def _normalize_payload(obj: Any) -> dict[str, Any]:
    """Convert generated recipe or other objects to a JSON-serializable dict.

    Prefer Pydantic model dump methods when available, then dict(), then the
    object itself as a string fallback.
    """
    try:
        if hasattr(obj, "model_dump"):
            result = obj.model_dump()
            return cast(dict[str, Any], result)
        if hasattr(obj, "dict"):
            result = obj.dict()
            return cast(dict[str, Any], result)
        if isinstance(obj, dict):
            return obj
        return {"value": str(obj)}
    except Exception:
        return {"value": str(obj)}
