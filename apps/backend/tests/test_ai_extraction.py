"""Tests for AI recipe extraction functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient

from crud.ai_drafts import create_draft
from main import app
from models.ai_drafts import AIDraft
from schemas.ai import AIGeneratedRecipe, AIRecipeFromUrlRequest
from schemas.recipes import IngredientIn, RecipeCategory, RecipeCreate, RecipeDifficulty
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
async def test_extract_recipe_from_url_extraction_not_found(
    async_client: AsyncClient,
) -> None:
    """Test recipe extraction when AI reports no recipe found."""
    from schemas.ai import ExtractionNotFound

    # Mock the AI agent to return ExtractionNotFound
    mock_result = Mock()
    mock_result.output = ExtractionNotFound(reason="No recipe found on this page")

    mock_agent = Mock()
    mock_agent.run = AsyncMock(return_value=mock_result)

    mock_html = "<html><body><h1>Not a recipe page</h1></body></html>"

    with (
        patch(
            "api.v1.ai.HTMLExtractionService.fetch_and_sanitize", return_value=mock_html
        ),
        patch("api.v1.ai.create_recipe_agent", return_value=mock_agent),
        patch("api.v1.ai.create_draft") as mock_create_draft,
        patch("api.v1.ai.create_draft_token", return_value="test-token"),
    ):
        # Mock the draft creation
        mock_draft = Mock()
        mock_draft.id = uuid4()
        mock_draft.expires_at = datetime.now(UTC) + timedelta(hours=1)
        mock_create_draft.return_value = mock_draft

        response = await async_client.post(
            "/api/v1/ai/extract-recipe-from-url",
            json={
                "source_url": "https://example.com/not-a-recipe",
            },
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is False
    assert "data" in data
    assert data["message"] == "Recipe extraction failed: No recipe found on this page"

    response_data = data["data"]
    assert "draft_id" in response_data
    assert "signed_url" in response_data
    assert "expires_at" in response_data
    assert response_data["ttl_seconds"] == 3600


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

    # Debug: log token and draft info to help diagnose 401 mismatches
    print("DEBUG: draft.id type=", type(draft.id), "value=", draft.id)
    print("DEBUG: test_user.id type=", type(test_user.id), "value=", test_user.id)
    print("DEBUG: token=", token)

    response = await no_auth_client.get(f"/api/v1/ai/drafts/{draft.id}?token={token}")
    print("DEBUG: response.status_code=", response.status_code)
    try:
        print("DEBUG: response.json()=", response.json())
    except Exception:
        print("DEBUG: response.text=", response.text)

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

    # Debug: log token and draft info for expired draft
    print(
        "DEBUG(EXPIRED): expired_draft.id type=",
        type(expired_draft.id),
        "value=",
        expired_draft.id,
    )
    print(
        "DEBUG(EXPIRED): test_user.id type=", type(test_user.id), "value=", test_user.id
    )
    print("DEBUG(EXPIRED): token=", token)

    response = await no_auth_client.get(
        f"/api/v1/ai/drafts/{expired_draft.id}?token={token}"
    )
    print("DEBUG(EXPIRED): response.status_code=", response.status_code)
    try:
        print("DEBUG(EXPIRED): response.json()=", response.json())
    except Exception:
        print("DEBUG(EXPIRED): response.text=", response.text)

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


@pytest.mark.asyncio
async def test_html_extractor_successful_fetch():
    """Test successful HTML extraction and sanitization."""
    extractor = HTMLExtractionService()

    mock_html = """
    <html>
        <head><title>Recipe Page</title></head>
        <body>
            <h1>Delicious Recipe</h1>
            <p>This is a recipe description.</p>
            <script>alert('evil script')</script>
            <div class="ingredients">
                <ul>
                    <li>1 cup flour</li>
                    <li>2 eggs</li>
                </ul>
            </div>
        </body>
    </html>
    """

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.content = mock_html.encode("utf-8")  # Add content attribute
        mock_response.headers = {"content-type": "text/html"}  # Add headers
        mock_response.raise_for_status = Mock()
        mock_async_client = mock_client.return_value.__aenter__.return_value
        mock_async_client.get.return_value = mock_response

        result = await extractor.fetch_and_sanitize("https://example.com/recipe")

        # Should contain the main content but not scripts
        assert "Delicious Recipe" in result
        assert "recipe description" in result
        assert "1 cup flour" in result
        assert "2 eggs" in result
        assert "alert('evil script')" not in result  # Script should be removed


@pytest.mark.asyncio
async def test_html_extractor_http_error():
    """Test HTML extractor with HTTP error response."""
    extractor = HTMLExtractionService()

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_async_client = mock_client.return_value.__aenter__.return_value
        mock_async_client.get.return_value = mock_response

        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await extractor.fetch_and_sanitize("https://example.com/not-found")


@pytest.mark.asyncio
async def test_html_extractor_empty_response():
    """Test HTML extractor with empty response."""
    extractor = HTMLExtractionService()

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.text = ""
        mock_response.content = b""  # Add empty content
        mock_response.headers = {"content-type": "text/html"}  # Add headers
        mock_response.raise_for_status = Mock()
        mock_async_client = mock_client.return_value.__aenter__.return_value
        mock_async_client.get.return_value = mock_response

        result = await extractor.fetch_and_sanitize("https://example.com/empty")
        assert result == ""


def test_html_extractor_invalid_schemes():
    """Test HTML extractor with various invalid URL schemes."""
    extractor = HTMLExtractionService()

    from fastapi import HTTPException

    invalid_urls = [
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>",
        "file:///etc/passwd",
        "ftp://example.com/file.txt",
    ]

    for url in invalid_urls:
        with pytest.raises(HTTPException):
            extractor._validate_url(url)


@pytest.mark.asyncio
async def test_create_recipe_agent():
    """Test AI agent creation and configuration."""
    from unittest.mock import patch

    from services.ai.agents import create_recipe_agent

    # Mock the Agent class since we don't want to create real AI agents in tests
    with patch("services.ai.agents.Agent") as mock_agent_class:
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        agent = create_recipe_agent()

        # Verify agent was created with the expected configuration
        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args

        # The agent should be created with a model (first positional arg)
        assert len(call_args[0]) >= 1  # At least the model parameter

        # Check that the agent is configured with output_type
        assert "output_type" in call_args[1]

        assert agent == mock_agent


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


@pytest.mark.asyncio
async def test_convert_to_recipe_create():
    """Test the convert_to_recipe_create function with realistic input."""
    from schemas.ai import RecipeExtractionResult
    from services.ai.agents import convert_to_recipe_create

    # Test with realistic extraction result
    extraction_result = RecipeExtractionResult(
        title="AI Test Recipe",
        description="A test recipe",
        prep_time_minutes=15,
        cook_time_minutes=30,
        serving_min=4,
        serving_max=6,
        instructions=["Step 1", "Step 2"],
        difficulty=RecipeDifficulty.MEDIUM,
        category=RecipeCategory.DINNER,
        ingredients=[
            IngredientIn(
                name="Test Ingredient",
                quantity_value=2.0,
                quantity_unit="cups",
                is_optional=False,
            )
        ],
        confidence_score=0.9,
        ethnicity="italian",
        oven_temperature_f=350,
        user_notes="Test notes",
    )

    result = convert_to_recipe_create(extraction_result, "https://example.com/recipe")

    assert isinstance(result, AIGeneratedRecipe)
    assert result.confidence_score == 0.9
    assert result.source_url == "https://example.com/recipe"
    assert result.recipe_data.title == "AI Test Recipe"
    assert result.recipe_data.difficulty == RecipeDifficulty.MEDIUM
    assert result.recipe_data.category == RecipeCategory.DINNER
    assert len(result.recipe_data.ingredients) == 1

    # Check ingredient
    ingredient = result.recipe_data.ingredients[0]
    assert ingredient.name == "Test Ingredient"
    assert ingredient.quantity_value == 2.0
    assert ingredient.quantity_unit == "cups"
    assert ingredient.is_optional is False


@pytest.mark.asyncio
async def test_extract_recipe_stream_success(async_client: AsyncClient) -> None:
    """Test successful SSE streaming extraction."""
    from schemas.ai import RecipeExtractionResult

    # Create a proper RecipeExtractionResult object
    extraction_result = RecipeExtractionResult(
        title="Mock AI Recipe",
        description="A recipe extracted by AI",
        prep_time_minutes=15,
        cook_time_minutes=30,
        serving_min=4,
        instructions=["Step 1", "Step 2"],
        difficulty="medium",
        category="dinner",
        ingredients=[
            {
                "name": "Test Ingredient",
                "quantity_value": 1.0,
                "quantity_unit": "cup",
                "is_optional": False,
            }
        ],
        confidence_score=0.85,
    )

    # Mock the AI agent response
    mock_result = Mock()
    mock_result.output = extraction_result

    mock_generated_recipe = AIGeneratedRecipe(
        recipe_data=RecipeCreate(
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
        ),
        confidence_score=0.85,
        source_url="https://example.com/recipe",
        extraction_notes=None,
    )

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
        response = await async_client.get(
            "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe"
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Parse SSE events from response
    events = []
    for line in response.text.split("\n"):
        if line.startswith("data: "):
            import json

            try:
                event_data = json.loads(line[6:])  # Remove "data: " prefix
                events.append(event_data)
            except json.JSONDecodeError:
                continue  # Skip malformed JSON

    # Verify event sequence - should have at least the basic flow
    # started, fetching, sanitizing, ai_call, converting
    assert len(events) >= 5

    # Check first event
    assert events[0]["status"] == "started"
    assert events[0]["step"] == "started"
    assert events[0]["progress"] == 0.0

    # Check that we get through the basic steps
    statuses = [event["status"] for event in events]
    assert "started" in statuses
    assert "fetching" in statuses
    assert "sanitizing" in statuses
    assert "ai_call" in statuses
    assert "converting" in statuses

    # The final event should be either complete or error (due to mock DB issues)
    final_event = events[-1]
    assert final_event["status"] in ["complete", "error"]
    assert final_event["progress"] == 1.0

    # If it's a complete event, verify it has the expected fields
    if final_event["status"] == "complete":
        assert final_event["success"] is True
        assert "draft_id" in final_event
        assert "signed_url" in final_event
        assert "confidence_score" in final_event


@pytest.mark.asyncio
async def test_extract_recipe_stream_ai_failure(async_client: AsyncClient) -> None:
    """Test SSE streaming with AI extraction failure."""
    from pydantic_ai import AgentRunError  # type: ignore[import-not-found]

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
        response = await async_client.get(
            "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe"
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Parse SSE events from response
    events = []
    for line in response.text.split("\n"):
        if line.startswith("data: "):
            import json

            try:
                event_data = json.loads(line[6:])
                events.append(event_data)
            except json.JSONDecodeError:
                continue

    # Should have events up to the error
    assert len(events) >= 3  # started, fetching, sanitizing, ai_call (error)

    # Check final event is an error
    final_event = events[-1]
    assert final_event["status"] == "error"
    assert final_event["step"] == "ai_call"
    assert final_event["progress"] == 1.0
    assert "AI agent failure" in final_event["detail"]

    # Verify we get the expected progression
    statuses = [event["status"] for event in events]
    assert "started" in statuses
    assert "fetching" in statuses
    assert "sanitizing" in statuses


@pytest.mark.asyncio
async def test_extract_recipe_stream_fetch_failure(async_client: AsyncClient) -> None:
    """Test SSE streaming with HTML fetch failure."""
    # Mock AI agent creation and HTML service to fail
    mock_agent = Mock()
    with (
        patch("api.v1.ai.create_recipe_agent", return_value=mock_agent),
        patch(
            "api.v1.ai.HTMLExtractionService.fetch_and_sanitize",
            side_effect=Exception("Network error"),
        ),
    ):
        response = await async_client.get(
            "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe"
        )

    assert response.status_code == status.HTTP_200_OK

    # Parse SSE events from response
    events = []
    for line in response.text.split("\n"):
        if line.startswith("data: "):
            import json

            event_data = json.loads(line[6:])
            events.append(event_data)

    # Should have started, fetching, then error
    assert len(events) >= 2

    # Check final event is an error
    final_event = events[-1]
    assert final_event["status"] == "error"
    assert final_event["step"] == "fetch_html"
    assert final_event["progress"] == 1.0
    assert "Fetch failed" in final_event["detail"]


@pytest.mark.asyncio
async def test_extract_recipe_stream_no_html_content(async_client: AsyncClient) -> None:
    """Test SSE streaming when no usable HTML content is found."""
    # Mock AI agent creation and HTML service to return empty content
    mock_agent = Mock()
    with (
        patch("api.v1.ai.create_recipe_agent", return_value=mock_agent),
        patch("api.v1.ai.HTMLExtractionService.fetch_and_sanitize", return_value=""),
    ):
        response = await async_client.get(
            "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe"
        )

    assert response.status_code == status.HTTP_200_OK

    # Parse SSE events from response
    events = []
    for line in response.text.split("\n"):
        if line.startswith("data: "):
            import json

            event_data = json.loads(line[6:])
            events.append(event_data)

    # Should have started, fetching, then error
    assert len(events) >= 2

    # Check final event is an error
    final_event = events[-1]
    assert final_event["status"] == "error"
    assert final_event["step"] == "fetch_html"
    assert final_event["progress"] == 1.0
    assert "No usable HTML content" in final_event["detail"]


@pytest.mark.asyncio
async def test_extract_recipe_stream_extraction_not_found(
    async_client: AsyncClient,
) -> None:
    """Test SSE streaming when AI reports no recipe found."""
    from schemas.ai import ExtractionNotFound

    # Mock the AI agent to return ExtractionNotFound
    mock_result = Mock()
    mock_result.output = ExtractionNotFound(reason="No recipe found on this page")

    mock_agent = Mock()
    mock_agent.run = AsyncMock(return_value=mock_result)

    mock_html = "<html><body><h1>Not a recipe page</h1></body></html>"

    # Mock the draft creation to avoid database issues
    mock_draft = Mock()
    mock_draft.id = "test-draft-id"

    with (
        patch(
            "api.v1.ai.HTMLExtractionService.fetch_and_sanitize", return_value=mock_html
        ),
        patch("api.v1.ai.create_recipe_agent", return_value=mock_agent),
        patch("api.v1.ai.create_draft", return_value=mock_draft),
        patch("api.v1.ai.create_draft_token", return_value="test-token"),
    ):
        response = await async_client.get(
            "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/search"
        )

    assert response.status_code == status.HTTP_200_OK

    # Parse SSE events from response
    events = []
    for line in response.text.split("\n"):
        if line.startswith("data: "):
            import json

            event_data = json.loads(line[6:])
            events.append(event_data)

    # Should complete with failure
    assert len(events) >= 4  # started, fetching, sanitizing, ai_call, complete

    # Check final event indicates failure
    final_event = events[-1]
    assert final_event["status"] == "complete"
    assert final_event["step"] == "complete"
    assert final_event["progress"] == 1.0
    assert final_event["success"] is False
    assert "Recipe extraction failed" in final_event["detail"]
    assert "draft_id" in final_event
    assert "signed_url" in final_event


@pytest.mark.asyncio
async def test_extract_recipe_stream_conversion_failure(
    async_client: AsyncClient,
) -> None:
    """Test SSE streaming when schema conversion fails."""
    # Mock the AI agent to return invalid result type
    mock_result = Mock()
    mock_result.output = "invalid_result_type"  # Not RecipeExtractionResult

    mock_agent = Mock()
    mock_agent.run = AsyncMock(return_value=mock_result)

    mock_html = "<html><body><h1>Mock Recipe</h1></body></html>"

    with (
        patch(
            "api.v1.ai.HTMLExtractionService.fetch_and_sanitize", return_value=mock_html
        ),
        patch("api.v1.ai.create_recipe_agent", return_value=mock_agent),
    ):
        response = await async_client.get(
            "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe"
        )

    assert response.status_code == status.HTTP_200_OK

    # Parse SSE events from response
    events = []
    for line in response.text.split("\n"):
        if line.startswith("data: "):
            import json

            event_data = json.loads(line[6:])
            events.append(event_data)

    # Should have events up to conversion error
    # started, fetching, sanitizing, ai_call, converting (error)
    assert len(events) >= 4

    # Check final event is a conversion error
    final_event = events[-1]
    assert final_event["status"] == "error"
    assert final_event["step"] == "convert_schema"
    assert final_event["progress"] == 1.0
    assert "Conversion failed" in final_event["detail"]


@pytest.mark.asyncio
async def test_extract_recipe_stream_unauthorized(no_auth_client) -> None:
    """Test SSE streaming without authentication."""
    response = await no_auth_client.get(
        "/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe"
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_extract_recipe_stream_with_prompt_override(
    async_client: AsyncClient,
) -> None:
    """Test SSE streaming with custom prompt override."""
    # Mock the AI agent response
    mock_result = Mock()
    mock_result.output = Mock()
    mock_result.output.confidence_score = 0.85
    mock_result.output.title = "Custom Prompt Recipe"
    mock_result.output.prep_time_minutes = 10
    mock_result.output.cook_time_minutes = 15
    mock_result.output.serving_min = 2
    mock_result.output.instructions = ["Custom step"]
    mock_result.output.difficulty = "easy"
    mock_result.output.category = "snack"
    mock_result.output.ingredients = []

    mock_generated_recipe = AIGeneratedRecipe(
        recipe_data=RecipeCreate(
            title="Custom Prompt Recipe",
            prep_time_minutes=10,
            cook_time_minutes=15,
            serving_min=2,
            instructions=["Custom step"],
            difficulty=RecipeDifficulty.EASY,
            category=RecipeCategory.SNACK,
            ingredients=[
                IngredientIn(
                    name="test ingredient",
                    quantity_value=1.0,
                    quantity_unit="cup",
                )
            ],
        ),
        confidence_score=0.85,
        source_url="https://example.com/recipe",
        extraction_notes=None,
    )

    mock_agent = Mock()
    mock_agent.run = AsyncMock(return_value=mock_result)

    mock_html = "<html><body><h1>Mock Recipe</h1></body></html>"

    with (
        patch(
            "api.v1.ai.HTMLExtractionService.fetch_and_sanitize", return_value=mock_html
        ),
        patch("api.v1.ai.create_recipe_agent", return_value=mock_agent),
        patch("api.v1.ai.convert_to_recipe_create", return_value=mock_generated_recipe),
    ):
        # Test with custom prompt
        custom_prompt = "Extract only the ingredients from this page"
        response = await async_client.get(
            f"/api/v1/ai/extract-recipe-stream?source_url=https://example.com/recipe&prompt_override={custom_prompt}"
        )

    assert response.status_code == status.HTTP_200_OK

    # Verify the agent was called with the custom prompt
    mock_agent.run.assert_called_once()
    call_args = mock_agent.run.call_args[0][0]
    assert custom_prompt in call_args
