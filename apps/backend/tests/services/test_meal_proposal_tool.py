"""Tests for the meal proposal tool."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic_ai import models

from services.chat_agent.tools.meal_proposals import tool_propose_meal_for_day


# Block any real model requests in tests
models.ALLOW_MODEL_REQUESTS = False


class MockUser:
    """Mock user for testing."""

    def __init__(self, user_id: uuid.UUID | None = None) -> None:
        self.id = user_id or uuid.uuid4()


class MockChatAgentDeps:
    """Mock dependencies for chat agent tools."""

    def __init__(
        self,
        db: AsyncMock | None = None,
        user: MockUser | None = None,
        user_preferences: Any = None,
        memory_content: str | None = None,
    ) -> None:
        self.db = db or AsyncMock()
        self.user = user or MockUser()
        self.user_preferences = user_preferences
        self.memory_content = memory_content


class MockRunContext:
    """Mock RunContext for testing tool functions."""

    def __init__(self, deps: MockChatAgentDeps | None = None) -> None:
        self.deps = deps or MockChatAgentDeps()


class TestProposeMealForDayTool:
    """Tests for the propose_meal_for_day tool function."""

    @pytest.mark.asyncio
    async def test_propose_existing_recipe_successfully(self) -> None:
        """Test proposing an existing recipe from user's collection."""
        # Arrange
        ctx = MockRunContext()
        recipe_id = str(uuid.uuid4())

        # Act
        result = await tool_propose_meal_for_day(
            ctx=ctx,
            date="2026-01-26",
            day_label="Sunday",
            existing_recipe_id=recipe_id,
            existing_recipe_title="Mom's Lasagna",
            existing_recipe_image_url="https://example.com/lasagna.jpg",
            existing_recipe_detail_path=f"/recipes/{recipe_id}",
        )

        # Assert
        assert result["status"] == "ok"
        assert "meal_proposal" in result
        proposal = result["meal_proposal"]
        assert proposal["type"] == "meal_proposal"
        assert proposal["date"] == "2026-01-26"
        assert proposal["day_label"] == "Sunday"
        assert proposal["proposal_id"] == "2026-01-26-proposal"
        assert proposal["existing_recipe"]["id"] == recipe_id
        assert proposal["existing_recipe"]["title"] == "Mom's Lasagna"
        assert (
            proposal["existing_recipe"]["image_url"]
            == "https://example.com/lasagna.jpg"
        )
        assert proposal["existing_recipe"]["detail_path"] == f"/recipes/{recipe_id}"
        assert proposal["new_recipe"] is None
        assert proposal["is_leftover"] is False
        assert proposal["is_eating_out"] is False
        assert "Proposed Mom's Lasagna for Sunday" in result["message"]

    @pytest.mark.asyncio
    async def test_propose_new_recipe_from_web(self) -> None:
        """Test proposing a new recipe from web search."""
        # Arrange
        ctx = MockRunContext()

        # Act
        result = await tool_propose_meal_for_day(
            ctx=ctx,
            date="2026-01-27",
            day_label="Monday",
            new_recipe_title="Korean BBQ Tacos",
            new_recipe_source_url="https://example.com/korean-bbq-tacos",
            new_recipe_description="Fusion tacos with Korean marinated beef",
        )

        # Assert
        assert result["status"] == "ok"
        proposal = result["meal_proposal"]
        assert proposal["type"] == "meal_proposal"
        assert proposal["date"] == "2026-01-27"
        assert proposal["day_label"] == "Monday"
        assert proposal["existing_recipe"] is None
        assert proposal["new_recipe"]["title"] == "Korean BBQ Tacos"
        assert (
            proposal["new_recipe"]["source_url"]
            == "https://example.com/korean-bbq-tacos"
        )
        assert (
            proposal["new_recipe"]["description"]
            == "Fusion tacos with Korean marinated beef"
        )
        assert proposal["is_leftover"] is False
        assert proposal["is_eating_out"] is False

    @pytest.mark.asyncio
    async def test_propose_leftover_day(self) -> None:
        """Test proposing a leftover day."""
        # Arrange
        ctx = MockRunContext()

        # Act
        result = await tool_propose_meal_for_day(
            ctx=ctx,
            date="2026-01-28",
            day_label="Tuesday",
            is_leftover=True,
            notes="Lasagna from Sunday should feed 4 people twice",
        )

        # Assert
        assert result["status"] == "ok"
        proposal = result["meal_proposal"]
        assert proposal["type"] == "meal_proposal"
        assert proposal["is_leftover"] is True
        assert proposal["is_eating_out"] is False
        assert proposal["existing_recipe"] is None
        assert proposal["new_recipe"] is None
        assert proposal["notes"] == "Lasagna from Sunday should feed 4 people twice"

    @pytest.mark.asyncio
    async def test_propose_eating_out(self) -> None:
        """Test proposing an eating out entry."""
        # Arrange
        ctx = MockRunContext()

        # Act
        result = await tool_propose_meal_for_day(
            ctx=ctx,
            date="2026-01-29",
            day_label="Wednesday",
            is_eating_out=True,
            notes="Weekly date night at Italian restaurant",
        )

        # Assert
        assert result["status"] == "ok"
        proposal = result["meal_proposal"]
        assert proposal["type"] == "meal_proposal"
        assert proposal["is_eating_out"] is True
        assert proposal["is_leftover"] is False
        assert proposal["existing_recipe"] is None
        assert proposal["new_recipe"] is None
        assert proposal["notes"] == "Weekly date night at Italian restaurant"

    @pytest.mark.asyncio
    async def test_propose_with_notes(self) -> None:
        """Test proposing a meal with contextual notes."""
        # Arrange
        ctx = MockRunContext()
        recipe_id = str(uuid.uuid4())

        # Act
        result = await tool_propose_meal_for_day(
            ctx=ctx,
            date="2026-01-30",
            day_label="Thursday",
            existing_recipe_id=recipe_id,
            existing_recipe_title="Quick Stir Fry",
            notes="Uses leftover scallions from Tuesday's Korean BBQ Tacos",
        )

        # Assert
        assert result["status"] == "ok"
        proposal = result["meal_proposal"]
        assert (
            proposal["notes"]
            == "Uses leftover scallions from Tuesday's Korean BBQ Tacos"
        )
        assert proposal["existing_recipe"]["title"] == "Quick Stir Fry"

    @pytest.mark.asyncio
    async def test_proposal_id_format(self) -> None:
        """Test that proposal_id follows expected format."""
        # Arrange
        ctx = MockRunContext()

        # Act
        result = await tool_propose_meal_for_day(
            ctx=ctx,
            date="2026-02-01",
            day_label="Saturday",
            new_recipe_title="Test Recipe",
            new_recipe_source_url="https://example.com/test",
        )

        # Assert
        proposal = result["meal_proposal"]
        assert proposal["proposal_id"] == "2026-02-01-proposal"

    @pytest.mark.asyncio
    async def test_minimal_existing_recipe_proposal(self) -> None:
        """Test proposing existing recipe with minimal fields."""
        # Arrange
        ctx = MockRunContext()
        recipe_id = str(uuid.uuid4())

        # Act
        result = await tool_propose_meal_for_day(
            ctx=ctx,
            date="2026-02-02",
            day_label="Sunday",
            existing_recipe_id=recipe_id,
            existing_recipe_title="Simple Pasta",
            # No image_url or detail_path
        )

        # Assert
        proposal = result["meal_proposal"]
        assert proposal["existing_recipe"]["id"] == recipe_id
        assert proposal["existing_recipe"]["title"] == "Simple Pasta"
        assert proposal["existing_recipe"]["image_url"] is None
        assert proposal["existing_recipe"]["detail_path"] is None
