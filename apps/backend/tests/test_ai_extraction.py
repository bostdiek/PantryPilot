"""Tests for AI recipe extraction functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from crud.ai_drafts import create_draft
from main import app
from models.ai_drafts import AIDraft
from schemas.ai import AIGeneratedRecipe, AIRecipeFromUrlRequest
from schemas.recipes import RecipeCategory, RecipeCreate, RecipeDifficulty
from services.ai.html_extractor import HTMLExtractionService


@pytest_asyncio.fixture
async def no_auth_client():
    """AsyncClient without authentication override for testing draft retrieval."""
    # Remove any auth overrides to test the actual endpoint behavior
    from dependencies.auth import get_current_user

    # Store original overrides
    original_overrides = dict(app.dependency_overrides)

    # Remove auth override if it exists
    app.dependency_overrides.pop(get_current_user, None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    # Restore original overrides
    app.dependency_overrides = original_overrides


@pytest.mark.asyncio
async def test_extract_recipe_from_url_success(
    async_client: AsyncClient, async_db_session
) -> None:
    """Test successful recipe extraction from URL."""
    # Mock the AI agent response
    mock_recipe_data = RecipeCreate(
        title="Mock AI Recipe",
        description="A recipe extracted by AI",
        prep_time_minutes=15,
        cook_time_minutes=30,
        serving_min=4,
        instructions=["Step 1", "Step 2"],
        difficulty=RecipeDifficulty.MEDIUM,
        category=RecipeCategory.DINNER,
        ingredients=[
            {
                "name": "Test Ingredient",
                "quantity_value": 1.0,
                "quantity_unit": "cup",
                "is_optional": False,
            }
        ],
    )

    mock_generated_recipe = AIGeneratedRecipe(
        recipe_data=mock_recipe_data,
        confidence_score=0.85,
        source_url="https://example.com/recipe",
        extraction_notes=None,
    )

    mock_result = Mock()
    mock_result.data = Mock()
    mock_result.data.confidence_score = 0.85

    # Mock the AI agent
    mock_agent = Mock()
    mock_agent.run = AsyncMock(return_value=mock_result)

    # Mock the HTML service
    mock_html = "<html><body><h1>Mock Recipe</h1></body></html>"

    with (
        patch(
            "api.v1.ai.HTMLExtractionService.fetch_and_sanitize", return_value=mock_html
        ),
        patch("api.v1.ai.create_recipe_agent", return_value=mock_agent),
        patch("api.v1.ai.convert_to_recipe_create", return_value=mock_generated_recipe),
    ):
        response = await async_client.post(
            "/api/v1/ai/extract-recipe-from-url",
            json={
                "source_url": "https://example.com/recipe",
            },
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert "data" in data

    response_data = data["data"]
    assert "draft_id" in response_data
    assert "signed_url" in response_data
    assert "expires_at" in response_data
    assert response_data["ttl_seconds"] == 3600


@pytest.mark.asyncio
async def test_extract_recipe_from_url_invalid_url(async_client: AsyncClient) -> None:
    """Test recipe extraction with invalid URL."""
    response = await async_client.post(
        "/api/v1/ai/extract-recipe-from-url",
        json={
            "source_url": "not-a-valid-url",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_extract_recipe_from_url_unauthorized(no_auth_client) -> None:
    """Test recipe extraction without authentication."""
    response = await no_auth_client.post(
        "/api/v1/ai/extract-recipe-from-url",
        json={
            "source_url": "https://example.com/recipe",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_extract_recipe_ai_failure(async_client: AsyncClient) -> None:
    """Test handling of AI extraction failure."""
    from pydantic_ai import AgentRunError

    # Mock the AI agent to raise an exception
    mock_agent = Mock()
    mock_agent.run = AsyncMock(side_effect=AgentRunError("AI processing failed"))

    mock_html = "<html><body><h1>Mock Recipe</h1></body></html>"

    with (
        patch(
            "api.v1.ai.HTMLExtractionService.fetch_and_sanitize", return_value=mock_html
        ),
        patch("api.v1.ai.create_recipe_agent", return_value=mock_agent),
    ):
        response = await async_client.post(
            "/api/v1/ai/extract-recipe-from-url",
            json={
                "source_url": "https://example.com/recipe",
            },
        )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    data = response.json()
    assert data["success"] is False
    assert "error" in data
    # The error is handled by the global error handler, so it will be in
    # error.message or similar


@pytest.mark.asyncio
async def test_get_ai_draft_success(no_auth_client, async_db_session) -> None:
    """Test successful retrieval of AI draft."""
    # Create a test draft in the database
    from models.users import User

    # Create a test user first
    test_user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed",  # pragma: allowlist secret
    )
    async_db_session.add(test_user)
    await async_db_session.commit()
    await async_db_session.refresh(test_user)

    draft_payload = {
        "generated_recipe": {
            "recipe_data": {
                "title": "Test Recipe",
                "instructions": ["Step 1"],
                "ingredients": [],
                "prep_time_minutes": 10,
                "cook_time_minutes": 20,
                "serving_min": 2,
                "difficulty": "easy",
                "category": "dinner",
            }
        }
    }

    draft = await create_draft(
        db=async_db_session,
        user_id=test_user.id,
        draft_type="recipe_suggestion",
        payload=draft_payload,
        source_url="https://example.com/recipe",
    )

    # Create a valid token
    from core.security import create_draft_token

    token = create_draft_token(draft.id, test_user.id)

    response = await no_auth_client.get(f"/api/v1/ai/drafts/{draft.id}?token={token}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["data"]["type"] == "recipe_suggestion"
    assert data["data"]["payload"] == draft_payload


@pytest.mark.asyncio
async def test_get_ai_draft_invalid_token(no_auth_client) -> None:
    """Test draft retrieval with invalid token."""
    fake_draft_id = "12345678-1234-5678-9012-123456789012"

    response = await no_auth_client.get(
        f"/api/v1/ai/drafts/{fake_draft_id}?token=invalid-token"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_ai_draft_expired(no_auth_client, async_db_session) -> None:
    """Test retrieval of expired draft."""
    from models.users import User

    # Create a test user
    test_user = User(
        username="testuser2",
        email="test2@example.com",
        hashed_password="hashed",  # pragma: allowlist secret
    )
    async_db_session.add(test_user)
    await async_db_session.commit()
    await async_db_session.refresh(test_user)

    # Create an expired draft
    expired_draft = AIDraft(
        user_id=test_user.id,
        type="recipe_suggestion",
        payload={"test": "data"},
        expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
    )
    async_db_session.add(expired_draft)
    await async_db_session.commit()
    await async_db_session.refresh(expired_draft)

    # Create token for the expired draft
    from core.security import create_draft_token

    token = create_draft_token(expired_draft.id, test_user.id)

    response = await no_auth_client.get(
        f"/api/v1/ai/drafts/{expired_draft.id}?token={token}"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_html_extractor_validate_url():
    """Test HTML extractor URL validation."""
    extractor = HTMLExtractionService()

    # Test valid URLs - should not raise
    extractor._validate_url("https://example.com/recipe")
    extractor._validate_url("http://example.com/recipe")

    # Test invalid URLs - should raise
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        extractor._validate_url("not-a-url")

    with pytest.raises(HTTPException):
        extractor._validate_url("ftp://example.com")

    with pytest.raises(HTTPException):
        extractor._validate_url("http://localhost/recipe")


@pytest.mark.asyncio
async def test_html_extractor_fetch_timeout():
    """Test HTML extractor timeout handling."""
    extractor = HTMLExtractionService(timeout=1)  # Very short timeout

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = Exception(
            "Timeout"
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await extractor.fetch_and_sanitize("https://example.com/very-slow-page")


def test_ai_recipe_from_url_request_validation():
    """Test AIRecipeFromUrlRequest schema validation."""
    # Valid request
    valid_request = AIRecipeFromUrlRequest(
        source_url="https://example.com/recipe", prompt_override="Custom prompt"
    )
    assert str(valid_request.source_url) == "https://example.com/recipe"
    assert valid_request.prompt_override == "Custom prompt"

    # Valid request without prompt override
    minimal_request = AIRecipeFromUrlRequest(source_url="https://example.com/recipe")
    assert minimal_request.prompt_override is None

    # Invalid URL should raise validation error
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AIRecipeFromUrlRequest(source_url="not-a-url")


def test_ai_generated_recipe_schema():
    """Test AIGeneratedRecipe schema."""
    from schemas.recipes import IngredientIn

    recipe_data = RecipeCreate(
        title="Test Recipe",
        prep_time_minutes=10,
        cook_time_minutes=20,
        serving_min=2,
        instructions=["Step 1", "Step 2"],
        difficulty=RecipeDifficulty.EASY,
        category=RecipeCategory.LUNCH,
        ingredients=[
            IngredientIn(
                name="Test Ingredient", quantity_value=1.0, quantity_unit="cup"
            )
        ],
    )

    ai_recipe = AIGeneratedRecipe(
        recipe_data=recipe_data,
        confidence_score=0.9,
        source_url="https://example.com/recipe",
        extraction_notes="Good extraction",
    )

    assert ai_recipe.confidence_score == 0.9
    assert ai_recipe.recipe_data.title == "Test Recipe"
    assert len(ai_recipe.recipe_data.ingredients) == 1
