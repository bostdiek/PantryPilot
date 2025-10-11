"""API tests for image-based AI recipe extraction endpoint."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import status
from httpx import ASGITransport, AsyncClient
from PIL import Image

from main import app


pytest_plugins = ("tests.fixtures.ai_fixtures",)


def create_test_image(
    width: int = 800, height: int = 600, format: str = "JPEG"
) -> bytes:
    """Create a test image in memory."""
    img = Image.new("RGB", (width, height), color="white")
    output = io.BytesIO()
    img.save(output, format=format)
    return output.getvalue()


@pytest_asyncio.fixture
async def no_auth_client():
    """Test client without authentication."""
    from dependencies.auth import get_current_user

    original = dict(app.dependency_overrides)
    app.dependency_overrides.pop(get_current_user, None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides = original


@pytest.mark.asyncio
async def test_extract_recipe_from_image_success(
    async_client: AsyncClient,
    sample_extraction_result,
    sample_ai_generated_recipe,
) -> None:
    """Happy path: upload image and extract recipe successfully."""
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from services.ai.models import DraftOutcome

    # Create test image
    test_image = create_test_image()

    # Create a mock draft
    mock_draft = AsyncMock()
    mock_draft.id = uuid4()
    mock_draft.expires_at = datetime.now(UTC) + timedelta(hours=1)

    # Create a mock service that returns DraftOutcome
    mock_service = AsyncMock()
    mock_service.extract_recipe_from_images = AsyncMock(
        return_value=DraftOutcome(
            draft=mock_draft,
            token="test-token",
            success=True,
        )
    )

    # Override the service dependency
    from services.ai.orchestrator import get_ai_extraction_service

    app.dependency_overrides[get_ai_extraction_service] = lambda: mock_service

    try:
        # Make request
        files = {"files": ("recipe.jpg", test_image, "image/jpeg")}
        resp = await async_client.post(
            "/api/v1/ai/extract-recipe-from-image",
            files=files,
        )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        # Stable contract keys
        for key in ("draft_id", "signed_url", "expires_at", "ttl_seconds"):
            assert key in data
        assert data["ttl_seconds"] == 3600
    finally:
        # Clean up override
        app.dependency_overrides.pop(get_ai_extraction_service, None)


@pytest.mark.asyncio
async def test_extract_recipe_from_image_no_files(
    async_client: AsyncClient,
) -> None:
    """Test error when no files are uploaded."""
    resp = await async_client.post(
        "/api/v1/ai/extract-recipe-from-image",
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_extract_recipe_from_image_unsupported_format(
    async_client: AsyncClient,
) -> None:
    """Test error with unsupported image format."""
    # Create a GIF image
    test_image = create_test_image(format="GIF")

    files = {"files": ("recipe.gif", test_image, "image/gif")}
    resp = await async_client.post(
        "/api/v1/ai/extract-recipe-from-image",
        files=files,
    )

    assert resp.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    body = resp.json()
    assert "Unsupported image type" in body.get("detail", "")


@pytest.mark.asyncio
async def test_extract_recipe_from_image_file_too_large(
    async_client: AsyncClient,
) -> None:
    """Test error when file size exceeds per-file limit."""
    # Create a large image (simulate > 8 MiB)
    with patch("services.images.normalize.validate_file_size") as mock_validate:
        from services.images.normalize import ImageSizeLimitError

        mock_validate.side_effect = ImageSizeLimitError("File too large")

        test_image = create_test_image()
        files = {"files": ("recipe.jpg", test_image, "image/jpeg")}
        resp = await async_client.post(
            "/api/v1/ai/extract-recipe-from-image",
            files=files,
        )

    assert resp.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


@pytest.mark.asyncio
async def test_extract_recipe_from_image_combined_size_too_large(
    async_client: AsyncClient,
) -> None:
    """Test error when combined file size exceeds limit."""
    # Create multiple images
    test_image = create_test_image()

    with patch("services.images.normalize.validate_combined_size") as mock_validate:
        from services.images.normalize import ImageSizeLimitError

        mock_validate.side_effect = ImageSizeLimitError("Combined size too large")

        files = [
            ("files", ("recipe1.jpg", test_image, "image/jpeg")),
            ("files", ("recipe2.jpg", test_image, "image/jpeg")),
        ]
        resp = await async_client.post(
            "/api/v1/ai/extract-recipe-from-image",
            files=files,
        )

    assert resp.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


@pytest.mark.asyncio
async def test_extract_recipe_from_image_extraction_not_found(
    async_client: AsyncClient,
    extraction_not_found,
) -> None:
    """Test when AI cannot find recipe in image."""
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from services.ai.models import DraftOutcome

    test_image = create_test_image()

    # Create a mock draft for failure case
    mock_draft = AsyncMock()
    mock_draft.id = uuid4()
    mock_draft.expires_at = datetime.now(UTC) + timedelta(hours=1)

    # Create a mock service that returns DraftOutcome with success=False
    mock_service = AsyncMock()
    mock_service.extract_recipe_from_images = AsyncMock(
        return_value=DraftOutcome(
            draft=mock_draft,
            token="test-token",
            success=False,
        )
    )

    # Override the service dependency
    from services.ai.orchestrator import get_ai_extraction_service

    app.dependency_overrides[get_ai_extraction_service] = lambda: mock_service

    try:
        files = {"files": ("recipe.jpg", test_image, "image/jpeg")}
        resp = await async_client.post(
            "/api/v1/ai/extract-recipe-from-image",
            files=files,
        )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is False
        assert "No recipe found" in body.get("message", "")
    finally:
        # Clean up override
        app.dependency_overrides.pop(get_ai_extraction_service, None)


@pytest.mark.asyncio
async def test_extract_recipe_from_image_no_auth(
    no_auth_client: AsyncClient,
) -> None:
    """Test that authentication is required."""
    test_image = create_test_image()

    files = {"files": ("recipe.jpg", test_image, "image/jpeg")}
    resp = await no_auth_client.post(
        "/api/v1/ai/extract-recipe-from-image",
        files=files,
    )

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_extract_recipe_from_image_multiple_files(
    async_client: AsyncClient,
    sample_extraction_result,
    sample_ai_generated_recipe,
) -> None:
    """Test uploading multiple image files."""
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from services.ai.models import DraftOutcome

    test_image1 = create_test_image()
    test_image2 = create_test_image(width=1024, height=768)

    # Create a mock draft
    mock_draft = AsyncMock()
    mock_draft.id = uuid4()
    mock_draft.expires_at = datetime.now(UTC) + timedelta(hours=1)

    # Create a mock service that returns DraftOutcome
    mock_service = AsyncMock()
    mock_service.extract_recipe_from_images = AsyncMock(
        return_value=DraftOutcome(
            draft=mock_draft,
            token="test-token",
            success=True,
        )
    )

    # Override the service dependency
    from services.ai.orchestrator import get_ai_extraction_service

    app.dependency_overrides[get_ai_extraction_service] = lambda: mock_service

    try:
        files = [
            ("files", ("recipe1.jpg", test_image1, "image/jpeg")),
            ("files", ("recipe2.jpg", test_image2, "image/jpeg")),
        ]
        resp = await async_client.post(
            "/api/v1/ai/extract-recipe-from-image",
            files=files,
        )

        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["success"] is True
    finally:
        # Clean up override
        app.dependency_overrides.pop(get_ai_extraction_service, None)
