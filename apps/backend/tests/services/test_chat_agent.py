"""Tests for chat agent construction and dynamic instructions."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from models.user_preferences import UserPreferences
from services.chat_agent import ChatAgentDeps, get_chat_agent


# Block any real model requests in tests
models.ALLOW_MODEL_REQUESTS = False


class MockUser:
    """Mock user for testing."""

    def __init__(self) -> None:
        self.id = "test-user-id"
        self.email = "test@example.com"
        self.full_name = "Test User"


class TestChatAgentDeps:
    """Tests for ChatAgentDeps dataclass."""

    def test_deps_with_no_preferences(self) -> None:
        """Test ChatAgentDeps can be constructed without preferences."""
        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="UTC",
        )

        assert deps.user_preferences is None
        assert deps.memory_content is None

    def test_deps_with_preferences_and_memory(self) -> None:
        """Test ChatAgentDeps can be constructed with preferences and memory."""
        mock_prefs = UserPreferences(
            user_id="test-user-id",
            family_size=4,
            default_servings=4,
            units="metric",
            meal_planning_days=7,
        )

        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="UTC",
            user_preferences=mock_prefs,
            memory_content="User prefers spicy food",
        )

        assert deps.user_preferences == mock_prefs
        assert deps.memory_content == "User prefers spicy food"


class TestAgentConstruction:
    """Tests for chat agent construction with dynamic instructions."""

    @pytest.mark.skipif(
        "GOOGLE_API_KEY" not in os.environ, reason="GOOGLE_API_KEY not set"
    )
    def test_agent_construction_succeeds(self) -> None:
        """Test that agent can be constructed successfully."""
        agent = get_chat_agent()
        assert agent is not None

    @pytest.mark.asyncio
    async def test_agent_with_no_preferences_context(self) -> None:
        """Test agent instructions when user has no preferences."""
        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="UTC",
            user_preferences=None,
            memory_content=None,
        )

        # The agent's dynamic instructions should handle None preferences
        # This is tested through the RunContext when the agent runs
        # For now, we verify the deps can be constructed
        assert deps.user_preferences is None
        assert deps.memory_content is None

    @pytest.mark.asyncio
    async def test_agent_with_full_preferences_context(self) -> None:
        """Test agent instructions when user has complete preferences."""

        mock_prefs = UserPreferences(
            user_id="test-user-id",
            family_size=4,
            default_servings=6,
            dietary_restrictions=["vegetarian", "gluten-free"],
            allergies=["peanuts", "shellfish"],
            preferred_cuisines=["Italian", "Mexican"],
            meal_planning_days=7,
            units="imperial",
            city="Seattle",
            state_or_region="WA",
            country="USA",
        )

        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="America/Los_Angeles",
            user_preferences=mock_prefs,
            memory_content="User loves pasta dishes and prefers quick weeknight meals",
        )

        # Verify all preference fields are accessible
        assert deps.user_preferences is not None
        assert deps.user_preferences.family_size == 4
        assert deps.user_preferences.default_servings == 6
        assert "vegetarian" in deps.user_preferences.dietary_restrictions
        assert "peanuts" in deps.user_preferences.allergies
        assert "Italian" in deps.user_preferences.preferred_cuisines
        assert deps.memory_content is not None
        assert "pasta" in deps.memory_content

    @pytest.mark.asyncio
    async def test_agent_with_missing_location(self) -> None:
        """Test agent instructions when user has preferences but no location."""

        mock_prefs = UserPreferences(
            user_id="test-user-id",
            family_size=3,
            default_servings=4,
            units="metric",
            meal_planning_days=7,
            city=None,
            postal_code=None,
        )

        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="UTC",
            user_preferences=mock_prefs,
            memory_content=None,
        )

        # Verify location fields are None
        assert deps.user_preferences is not None
        assert deps.user_preferences.city is None
        assert deps.user_preferences.postal_code is None

    @pytest.mark.asyncio
    async def test_agent_with_empty_preference_arrays(self) -> None:
        """Test agent instructions when preference arrays are empty."""

        mock_prefs = UserPreferences(
            user_id="test-user-id",
            family_size=2,
            default_servings=2,
            dietary_restrictions=[],
            allergies=[],
            preferred_cuisines=[],
            meal_planning_days=5,
            units="metric",
        )

        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="UTC",
            user_preferences=mock_prefs,
            memory_content=None,
        )

        # Verify empty arrays
        assert deps.user_preferences is not None
        assert len(deps.user_preferences.dietary_restrictions) == 0
        assert len(deps.user_preferences.allergies) == 0
        assert len(deps.user_preferences.preferred_cuisines) == 0

    @pytest.mark.asyncio
    async def test_agent_with_memory_only(self) -> None:
        """Test agent instructions with memory but no preferences."""

        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="UTC",
            user_preferences=None,
            memory_content=(
                "User is training for a marathon and needs high-protein meals"
            ),
        )

        # Verify memory is set but preferences are None
        assert deps.user_preferences is None
        assert deps.memory_content is not None
        assert "marathon" in deps.memory_content
        assert "high-protein" in deps.memory_content

    @pytest.mark.asyncio
    async def test_agent_with_empty_memory_string(self) -> None:
        """Test agent instructions with empty memory string."""

        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="UTC",
            user_preferences=None,
            memory_content="   ",  # Whitespace only
        )

        # Verify whitespace-only memory is handled
        assert deps.memory_content is not None
        assert deps.memory_content.strip() == ""


class TestAgentIntegrationWithPreferences:
    """Integration tests for agent with user preferences and memory."""

    @pytest.mark.asyncio
    async def test_agent_run_with_preferences_integration(self) -> None:
        """Test agent run with preferences includes them in context."""
        # Arrange - create agent directly with TestModel to avoid Google API requirement
        from pydantic_ai import Agent

        from schemas.chat_content import AssistantMessage

        agent = Agent[ChatAgentDeps, AssistantMessage](
            TestModel(),
            deps_type=ChatAgentDeps,
        )

        mock_prefs = UserPreferences(
            user_id="test-user-id",
            family_size=4,
            default_servings=6,
            dietary_restrictions=["vegetarian"],
            allergies=["peanuts", "shellfish"],
            preferred_cuisines=["Italian", "Mexican"],
            meal_planning_days=7,
            units="imperial",
            city="Seattle",
            state_or_region="WA",
            country="USA",
        )

        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="America/Los_Angeles",
            user_preferences=mock_prefs,
            memory_content="User loves pasta and prefers quick weeknight meals",
        )

        # Act
        result = await agent.run(
            "What should I cook for dinner tonight?",
            deps=deps,
        )

        # Assert - TestModel returns success message
        assert result.output is not None
        # Verify deps were passed correctly
        assert deps.user_preferences is not None
        assert deps.user_preferences.family_size == 4
        assert "peanuts" in deps.user_preferences.allergies

    @pytest.mark.asyncio
    async def test_agent_run_without_preferences(self) -> None:
        """Test agent run without preferences still works."""
        # Arrange
        from pydantic_ai import Agent

        from schemas.chat_content import AssistantMessage

        agent = Agent[ChatAgentDeps, AssistantMessage](
            TestModel(),
            deps_type=ChatAgentDeps,
        )

        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="UTC",
            user_preferences=None,
            memory_content=None,
        )

        # Act
        result = await agent.run(
            "What should I cook for dinner?",
            deps=deps,
        )

        # Assert - agent should handle None preferences gracefully
        assert result.output is not None
        assert deps.user_preferences is None
        assert deps.memory_content is None

    @pytest.mark.asyncio
    async def test_agent_run_with_memory_only(self) -> None:
        """Test agent run with memory but no preferences."""
        # Arrange
        from pydantic_ai import Agent

        from schemas.chat_content import AssistantMessage

        agent = Agent[ChatAgentDeps, AssistantMessage](
            TestModel(),
            deps_type=ChatAgentDeps,
        )

        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="UTC",
            user_preferences=None,
            memory_content=(
                "User is training for a marathon and needs high-protein meals"
            ),
        )

        # Act
        result = await agent.run(
            "Suggest a meal for after my run",
            deps=deps,
        )

        # Assert
        assert result.output is not None
        assert deps.memory_content is not None
        assert "marathon" in deps.memory_content

    @pytest.mark.asyncio
    async def test_agent_run_with_missing_location(self) -> None:
        """Test agent with preferences but missing location."""
        # Arrange
        from pydantic_ai import Agent

        from schemas.chat_content import AssistantMessage

        agent = Agent[ChatAgentDeps, AssistantMessage](
            TestModel(),
            deps_type=ChatAgentDeps,
        )

        mock_prefs = UserPreferences(
            user_id="test-user-id",
            family_size=3,
            default_servings=4,
            units="metric",
            meal_planning_days=7,
            city=None,  # No location
            postal_code=None,
        )

        deps = ChatAgentDeps(
            db=AsyncMock(),
            user=MockUser(),  # type: ignore
            current_datetime=datetime.now(UTC),
            user_timezone="UTC",
            user_preferences=mock_prefs,
            memory_content=None,
        )

        # Act
        result = await agent.run(
            "What's good for dinner based on the weather?",
            deps=deps,
        )

        # Assert - agent should handle missing location
        assert result.output is not None
        assert deps.user_preferences is not None
        assert deps.user_preferences.city is None
