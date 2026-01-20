"""Canonical content block schemas for chat assistant responses.

Frontend rollout plan (incremental rendering):
1) text-only via streaming deltas
2) link blocks
3) recipe card blocks
4) action blocks with confirmation
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class TextBlock(BaseModel):
    """Plain text block."""

    type: Literal["text"]
    text: str

    model_config = ConfigDict(extra="forbid")


class LinkBlock(BaseModel):
    """Clickable link block."""

    type: Literal["link"]
    label: str
    href: HttpUrl

    model_config = ConfigDict(extra="forbid")


class RecipeCardBlock(BaseModel):
    """Recipe card block with optional deep link.

    The href field supports both absolute URLs (external recipes) and
    relative URLs (draft deep-links like /recipes/new?ai=1&draftId=...).

    For AI-suggested recipes, source_url contains the original external recipe
    URL while href contains the internal draft approval link.
    """

    type: Literal["recipe_card"]
    recipe_id: UUID | None = None
    title: str
    subtitle: str | None = None
    image_url: HttpUrl | None = None
    href: str | None = None
    source_url: str | None = None  # Original external recipe URL

    model_config = ConfigDict(extra="forbid")


class ActionBlock(BaseModel):
    """UI action block that may require confirmation."""

    type: Literal["action"]
    action_id: UUID
    label: str
    requires_confirmation: bool = True

    model_config = ConfigDict(extra="forbid")


ChatContentBlock = Annotated[
    TextBlock | LinkBlock | RecipeCardBlock | ActionBlock,
    Field(discriminator="type"),
]


class AssistantMessage(BaseModel):
    """Assistant response composed of canonical content blocks."""

    blocks: list[ChatContentBlock]

    model_config = ConfigDict(extra="forbid")
