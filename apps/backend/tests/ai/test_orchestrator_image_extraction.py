"""Unit tests for Orchestrator.extract_recipe_from_images method."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic_ai.messages import BinaryContent

from services.ai.models import DraftOutcome
from services.ai.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_extract_recipe_from_images_uses_binary_content() -> None:
    """Verify that extract_recipe_from_images passes BinaryContent to agent.run."""
    from schemas.ai import RecipeExtractionResult

    # Create mock components
    mock_html_extractor = MagicMock()
    mock_ai_agent = MagicMock()
    mock_converter = MagicMock()
    mock_draft_service = MagicMock()

    # Create a mock agent that we can inspect
    mock_agent_instance = AsyncMock()
    mock_result = MagicMock()
    
    # Create a simple extraction result
    extraction_result = RecipeExtractionResult(
        title="Test Recipe",
        prep_time_minutes=10,
        cook_time_minutes=20,
        serving_min=4,
        instructions=["Step 1", "Step 2"],
        difficulty="easy",
        category="dinner",
        ingredients=[
            {
                "name": "flour",
                "quantity_value": 2.0,
                "quantity_unit": "cups",
                "is_optional": False,
            }
        ],
        confidence_score=0.9,
    )
    mock_result.output = extraction_result
    mock_agent_instance.run = AsyncMock(return_value=mock_result)

    # Create mock draft
    mock_draft = MagicMock()
    mock_draft.id = uuid4()
    mock_draft.expires_at = datetime.now(UTC) + timedelta(hours=1)

    # Setup mock services
    mock_converter.convert_to_recipe_create = MagicMock(return_value=MagicMock())
    mock_draft_service.create_success_draft = AsyncMock(return_value=mock_draft)
    mock_draft_service.create_draft_token = MagicMock(return_value="test-token")

    # Create orchestrator with mocks
    orchestrator = Orchestrator(
        html_extractor=mock_html_extractor,
        ai_agent=mock_ai_agent,
        recipe_converter=mock_converter,
        draft_service=mock_draft_service,
    )

    # Prepare test data
    test_image_bytes = b"fake-jpeg-data"
    normalized_images = [test_image_bytes]
    
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = uuid4()

    # Patch the agent creation to return our mock
    with patch(
        "services.ai.agents.create_image_recipe_agent",
        return_value=mock_agent_instance,
    ):
        # Call the method
        outcome = await orchestrator.extract_recipe_from_images(
            normalized_images=normalized_images,
            db=mock_db,
            current_user=mock_user,
            prompt_override=None,
        )

    # Verify the agent.run was called
    assert mock_agent_instance.run.called
    
    # Get the call arguments
    call_args = mock_agent_instance.run.call_args[0][0]
    
    # Verify the messages structure
    assert isinstance(call_args, list)
    assert len(call_args) == 2  # prompt + 1 image
    
    # First element should be the prompt string
    assert isinstance(call_args[0], str)
    assert "Extract the complete recipe information" in call_args[0]
    
    # Second element should be BinaryContent
    assert isinstance(call_args[1], BinaryContent)
    assert call_args[1].data == test_image_bytes
    assert call_args[1].media_type == "image/jpeg"
    
    # Verify outcome is successful
    assert isinstance(outcome, DraftOutcome)
    assert outcome.success is True
    assert outcome.token == "test-token"


@pytest.mark.asyncio
async def test_extract_recipe_from_images_multiple_images() -> None:
    """Verify that multiple images are passed as separate BinaryContent objects."""
    from schemas.ai import RecipeExtractionResult

    # Create mock components
    mock_html_extractor = MagicMock()
    mock_ai_agent = MagicMock()
    mock_converter = MagicMock()
    mock_draft_service = MagicMock()

    # Create a mock agent
    mock_agent_instance = AsyncMock()
    mock_result = MagicMock()
    
    extraction_result = RecipeExtractionResult(
        title="Test Recipe",
        prep_time_minutes=10,
        cook_time_minutes=20,
        serving_min=4,
        instructions=["Step 1"],
        difficulty="easy",
        category="dinner",
        ingredients=[
            {
                "name": "sugar",
                "quantity_value": 1.0,
                "quantity_unit": "cup",
                "is_optional": False,
            }
        ],
        confidence_score=0.9,
    )
    mock_result.output = extraction_result
    mock_agent_instance.run = AsyncMock(return_value=mock_result)

    # Create mock draft
    mock_draft = MagicMock()
    mock_draft.id = uuid4()
    mock_draft.expires_at = datetime.now(UTC) + timedelta(hours=1)

    # Setup mock services
    mock_converter.convert_to_recipe_create = MagicMock(return_value=MagicMock())
    mock_draft_service.create_success_draft = AsyncMock(return_value=mock_draft)
    mock_draft_service.create_draft_token = MagicMock(return_value="test-token")

    # Create orchestrator
    orchestrator = Orchestrator(
        html_extractor=mock_html_extractor,
        ai_agent=mock_ai_agent,
        recipe_converter=mock_converter,
        draft_service=mock_draft_service,
    )

    # Prepare test data with multiple images
    image1_bytes = b"fake-jpeg-data-1"
    image2_bytes = b"fake-jpeg-data-2"
    image3_bytes = b"fake-jpeg-data-3"
    normalized_images = [image1_bytes, image2_bytes, image3_bytes]
    
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = uuid4()

    # Patch the agent creation
    with patch(
        "services.ai.agents.create_image_recipe_agent",
        return_value=mock_agent_instance,
    ):
        # Call the method
        outcome = await orchestrator.extract_recipe_from_images(
            normalized_images=normalized_images,
            db=mock_db,
            current_user=mock_user,
            prompt_override=None,
        )

    # Verify the agent.run was called
    assert mock_agent_instance.run.called
    
    # Get the call arguments
    call_args = mock_agent_instance.run.call_args[0][0]
    
    # Verify the messages structure
    assert isinstance(call_args, list)
    assert len(call_args) == 4  # prompt + 3 images
    
    # First element should be the prompt
    assert isinstance(call_args[0], str)
    
    # Next three elements should be BinaryContent for each image
    for i, expected_bytes in enumerate([image1_bytes, image2_bytes, image3_bytes], start=1):
        assert isinstance(call_args[i], BinaryContent)
        assert call_args[i].data == expected_bytes
        assert call_args[i].media_type == "image/jpeg"
    
    # Verify outcome is successful
    assert outcome.success is True


@pytest.mark.asyncio
async def test_extract_recipe_from_images_with_custom_prompt() -> None:
    """Verify that custom prompt override is used correctly."""
    from schemas.ai import RecipeExtractionResult

    mock_html_extractor = MagicMock()
    mock_ai_agent = MagicMock()
    mock_converter = MagicMock()
    mock_draft_service = MagicMock()

    mock_agent_instance = AsyncMock()
    mock_result = MagicMock()
    
    extraction_result = RecipeExtractionResult(
        title="Test Recipe",
        prep_time_minutes=10,
        cook_time_minutes=20,
        serving_min=4,
        instructions=["Step 1"],
        difficulty="easy",
        category="dinner",
        ingredients=[
            {
                "name": "butter",
                "quantity_value": 0.5,
                "quantity_unit": "cup",
                "is_optional": False,
            }
        ],
        confidence_score=0.9,
    )
    mock_result.output = extraction_result
    mock_agent_instance.run = AsyncMock(return_value=mock_result)

    mock_draft = MagicMock()
    mock_draft.id = uuid4()
    mock_draft.expires_at = datetime.now(UTC) + timedelta(hours=1)

    mock_converter.convert_to_recipe_create = MagicMock(return_value=MagicMock())
    mock_draft_service.create_success_draft = AsyncMock(return_value=mock_draft)
    mock_draft_service.create_draft_token = MagicMock(return_value="test-token")

    orchestrator = Orchestrator(
        html_extractor=mock_html_extractor,
        ai_agent=mock_ai_agent,
        recipe_converter=mock_converter,
        draft_service=mock_draft_service,
    )

    test_image_bytes = b"fake-jpeg-data"
    normalized_images = [test_image_bytes]
    
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = uuid4()

    custom_prompt = "Extract recipe with special focus on dietary restrictions"

    with patch(
        "services.ai.agents.create_image_recipe_agent",
        return_value=mock_agent_instance,
    ):
        await orchestrator.extract_recipe_from_images(
            normalized_images=normalized_images,
            db=mock_db,
            current_user=mock_user,
            prompt_override=custom_prompt,
        )

    # Verify custom prompt was used
    call_args = mock_agent_instance.run.call_args[0][0]
    assert call_args[0] == custom_prompt
