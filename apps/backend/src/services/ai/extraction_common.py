"""Shared extraction utilities used by multiple orchestrators.

Provides a small DraftManager that encapsulates draft creation and token
generation logic so URL and Image orchestrators can reuse identical
business rules without duplicating code.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from services.ai.draft_service import (
    create_draft_token,
    create_failure_draft,
    create_success_draft,
)
from services.ai.interfaces import DraftServiceProtocol


class DraftManager:
    """Small facade around draft_service helper functions.

    Keeps draft/token semantics central so orchestrators do not duplicate
    TTL or token creation logic.
    """

    def __init__(
        self, draft_service: DraftServiceProtocol | None = None, ttl_hours: int = 1
    ) -> None:
        self._ttl_hours = ttl_hours
        # Optional underlying protocol implementation (used in tests)
        self._svc = draft_service

    async def create_success_draft(
        self,
        db: AsyncSession,
        current_user: User,
        source_url: str,
        generated_recipe: Any,
        prompt_override: str | None = None,
    ) -> Any:
        if self._svc is not None:
            return await self._svc.create_success_draft(
                db, current_user, source_url, generated_recipe, prompt_override
            )
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
        if self._svc is not None:
            return await self._svc.create_failure_draft(
                db, current_user, source_url, extraction_not_found, prompt_override
            )
        return await create_failure_draft(
            db, current_user, source_url, extraction_not_found, prompt_override
        )

    def create_draft_token(
        self, draft_id: Any, user_id: Any, exp_delta: timedelta | None = None
    ) -> str:
        # Default TTL if none provided
        exp = exp_delta or timedelta(hours=self._ttl_hours)
        if self._svc is not None:
            return self._svc.create_draft_token(draft_id, user_id, exp)
        return create_draft_token(draft_id, user_id, exp)
