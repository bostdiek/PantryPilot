"""Schemas for user memory document API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserMemoryDocumentResponse(BaseModel):
    """Response schema for user memory document GET."""

    model_config = ConfigDict(from_attributes=True)

    content: str = Field(
        ...,
        description="Markdown-formatted memory content",
    )
    format: Literal["markdown"] = Field(
        default="markdown",
        description="Content format (currently only 'markdown' supported)",
    )
    version: int = Field(
        ...,
        description="Version counter incremented on each update",
        ge=1,
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
    )
    updated_by: Literal["assistant", "user"] = Field(
        ...,
        description="Who made the last update: 'assistant' or 'user'",
    )


class UserMemoryDocumentUpdate(BaseModel):
    """Request schema for user memory document PUT."""

    content: str = Field(
        ...,
        description="Updated markdown-formatted memory content",
        min_length=0,
        max_length=50000,
    )


class UserMemoryDocumentUpdateResponse(BaseModel):
    """Response schema for user memory document PUT."""

    model_config = ConfigDict(from_attributes=True)

    content: str = Field(
        ...,
        description="Updated markdown-formatted memory content",
    )
    format: Literal["markdown"] = Field(
        default="markdown",
        description="Content format",
    )
    version: int = Field(
        ...,
        description="New version number after update",
        ge=1,
    )
    updated_at: datetime = Field(
        ...,
        description="Update timestamp",
    )
    updated_by: Literal["user"] = Field(
        default="user",
        description="Updated by user via account settings",
    )
