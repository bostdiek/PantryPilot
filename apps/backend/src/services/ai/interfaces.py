"""Service interfaces for AI extraction functionality.

This module defines protocols/interfaces that enable clean dependency injection
and remove the need for dynamic function resolution and mock detection logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_drafts import AIDraft
from models.users import User
from schemas.ai import ExtractionNotFound, RecipeExtractionResult
from services.ai.models import DraftOutcome


class HTMLExtractorProtocol(Protocol):
    """Protocol for HTML extraction and sanitization."""

    async def fetch_sanitized_html(self, url: str) -> str:
        """Fetch and sanitize HTML content from a URL."""
        ...


class AIAgentProtocol(Protocol):
    """Protocol for AI recipe extraction agents."""

    async def run_extraction_agent(
        self, sanitized_html: str, prompt_override: str | None = None
    ) -> RecipeExtractionResult | ExtractionNotFound:
        """Run AI agent to extract recipe from HTML content."""
        ...


class RecipeConverterProtocol(Protocol):
    """Protocol for converting extraction results to recipe schemas."""

    def convert_to_recipe_create(
        self, extraction_result: RecipeExtractionResult, source_url: str
    ) -> Any:
        """Convert extraction result to a recipe create schema (returned as Any)."""
        ...


class DraftServiceProtocol(Protocol):
    """Protocol for AI draft management operations."""

    async def create_success_draft(
        self,
        db: AsyncSession,
        current_user: User,
        source_url: str,
        generated_recipe: Any,
        prompt_override: str | None = None,
    ) -> AIDraft:
        """Create a draft for successful recipe extraction."""
        ...

    async def create_failure_draft(
        self,
        db: AsyncSession,
        current_user: User,
        source_url: str,
        extraction_not_found: ExtractionNotFound,
        prompt_override: str | None = None,
    ) -> AIDraft:
        """Create a draft for failed recipe extraction.

        Phase 3 Refactor: unified return type (AIDraft) instead of (draft, message)
        to simplify orchestrator logic and eliminate ad-hoc tuple unpacking.
        Error messaging is now carried separately (e.g. via DraftOutcome.message
        or domain exceptions) rather than positional tuple elements.
        """
        ...

    def create_draft_token(
        self, draft_id: UUID, user_id: UUID, exp_delta: timedelta | None = None
    ) -> str:
        """Create a signed token for draft access."""
        ...


class AIExtractionService(ABC):
    """Abstract base class for AI extraction orchestration.

    This service coordinates the entire extraction pipeline:
    1. HTML fetching and sanitization
    2. AI agent processing
    3. Schema conversion
    4. Draft creation and token generation
    """

    def __init__(
        self,
        html_extractor: HTMLExtractorProtocol,
        ai_agent: AIAgentProtocol,
        recipe_converter: RecipeConverterProtocol,
        draft_service: DraftServiceProtocol,
    ) -> None:
        self.html_extractor = html_extractor
        self.ai_agent = ai_agent
        self.recipe_converter = recipe_converter
        self.draft_service = draft_service

    @abstractmethod
    async def extract_recipe_from_url(
        self,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> DraftOutcome[AIDraft]:
        """Extract recipe from URL and create draft (returns DraftOutcome)."""
        ...

    @abstractmethod
    def stream_extraction_progress(
        self,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Return an async generator that will stream extraction progress.

        Implementations should be async generator functions (i.e. `async def`
        with `yield`) so that calling this method returns an AsyncGenerator.
        """
        ...


# Streaming stage protocols for clean separation
class StreamingStageProtocol(Protocol):
    """Protocol for streaming extraction stages."""

    async def stream_stage_convert(
        self, extraction_result: Any, source_url: str
    ) -> tuple[Any | None, dict[str, Any] | None]:
        """Convert extraction result for streaming."""
        ...

    async def stream_stage_success_draft(
        self,
        generated_recipe: Any,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None,
    ) -> dict[str, Any]:
        """Create success draft for streaming."""
        ...

    async def stream_stage_failure_draft(
        self,
        extraction_not_found: ExtractionNotFound,
        source_url: str,
        db: AsyncSession,
        current_user: User,
        prompt_override: str | None,
    ) -> dict[str, Any]:
        """Create failure draft for streaming."""
        ...
