"""Tests for image normalization utilities."""

import io

import pytest
from PIL import Image

from services.images.normalize import (
    ImageFormatError,
    ImageSizeLimitError,
    normalize_image,
    normalize_images,
    validate_combined_size,
    validate_content_type,
    validate_file_size,
)


def create_test_image(
    width: int = 800, height: int = 600, mode: str = "RGB", format: str = "JPEG"
) -> bytes:
    """Create a test image in memory."""
    img = Image.new(mode, (width, height), color="white")
    output = io.BytesIO()
    img.save(output, format=format)
    return output.getvalue()


def test_validate_content_type_jpeg():
    """Test validation of JPEG content type."""
    validate_content_type("image/jpeg")  # Should not raise


def test_validate_content_type_png():
    """Test validation of PNG content type."""
    validate_content_type("image/png")  # Should not raise


def test_validate_content_type_invalid():
    """Test rejection of invalid content types."""
    with pytest.raises(ImageFormatError, match="Unsupported image type"):
        validate_content_type("image/gif")

    with pytest.raises(ImageFormatError, match="Unsupported image type"):
        validate_content_type("application/pdf")


def test_validate_file_size_ok():
    """Test file size validation within limit."""
    validate_file_size(1024 * 1024)  # 1 MiB - should pass


def test_validate_file_size_exceeds():
    """Test file size validation exceeding limit."""
    with pytest.raises(ImageSizeLimitError, match="exceeds per-file limit"):
        validate_file_size(10 * 1024 * 1024)  # 10 MiB - should fail


def test_validate_combined_size_ok():
    """Test combined size validation within limit."""
    sizes = [1024 * 1024, 2 * 1024 * 1024]  # 1 + 2 = 3 MiB
    validate_combined_size(sizes)  # Should pass


def test_validate_combined_size_exceeds():
    """Test combined size validation exceeding limit."""
    sizes = [10 * 1024 * 1024, 11 * 1024 * 1024]  # 21 MiB total
    with pytest.raises(ImageSizeLimitError, match="Combined file size"):
        validate_combined_size(sizes)


def test_normalize_image_basic():
    """Test basic image normalization."""
    test_image = create_test_image()
    normalized = normalize_image(test_image)

    # Verify output is valid JPEG
    img = Image.open(io.BytesIO(normalized))
    assert img.format == "JPEG"
    assert img.mode == "RGB"


def test_normalize_image_rgba_to_rgb():
    """Test conversion of RGBA image to RGB."""
    test_image = create_test_image(mode="RGBA", format="PNG")
    normalized = normalize_image(test_image)

    # Verify output is RGB JPEG
    img = Image.open(io.BytesIO(normalized))
    assert img.format == "JPEG"
    assert img.mode == "RGB"


def test_normalize_image_downscale():
    """Test downscaling of large images."""
    # Create 3000x2000 image
    test_image = create_test_image(width=3000, height=2000)
    normalized = normalize_image(test_image, max_dimension=2048)

    # Verify image was downscaled
    img = Image.open(io.BytesIO(normalized))
    assert img.width <= 2048
    assert img.height <= 2048
    # Aspect ratio preserved
    assert abs((img.width / img.height) - (3000 / 2000)) < 0.01


def test_normalize_image_no_downscale_needed():
    """Test that small images are not upscaled."""
    test_image = create_test_image(width=800, height=600)
    normalized = normalize_image(test_image, max_dimension=2048)

    # Verify image dimensions unchanged
    img = Image.open(io.BytesIO(normalized))
    assert img.width == 800
    assert img.height == 600


def test_normalize_image_invalid_data():
    """Test handling of invalid image data."""
    from services.images.normalize import ImageValidationError

    invalid_data = b"not an image"
    with pytest.raises(ImageValidationError, match="Failed to process image"):
        normalize_image(invalid_data)


def test_normalize_images_multiple():
    """Test normalizing multiple images."""
    image1 = create_test_image(width=800, height=600)
    image2 = create_test_image(width=1024, height=768)

    image_files = [
        (image1, "image/jpeg"),
        (image2, "image/jpeg"),
    ]

    normalized = normalize_images(image_files)

    assert len(normalized) == 2
    # Verify both are valid JPEGs
    for img_bytes in normalized:
        img = Image.open(io.BytesIO(img_bytes))
        assert img.format == "JPEG"
        assert img.mode == "RGB"


def test_normalize_images_validation_fails():
    """Test that normalization fails with invalid files."""
    image1 = create_test_image(format="GIF")

    image_files = [
        (image1, "image/gif"),  # Unsupported format
    ]

    with pytest.raises(ImageFormatError):
        normalize_images(image_files)


def test_normalize_images_size_limit():
    """Test that normalization fails with oversized files."""
    # Mock the size to be over limit - create oversized data
    with pytest.raises(ImageSizeLimitError):
        normalize_images([(b"x" * (9 * 1024 * 1024), "image/jpeg")])


def test_normalize_image_preserves_aspect_ratio_landscape():
    """Test that landscape images preserve aspect ratio when downscaled."""
    test_image = create_test_image(width=3200, height=1800)
    normalized = normalize_image(test_image, max_dimension=2048)

    img = Image.open(io.BytesIO(normalized))
    # Width should be at max dimension
    assert img.width == 2048
    # Height should maintain aspect ratio
    expected_height = int(1800 * (2048 / 3200))
    assert abs(img.height - expected_height) <= 1  # Allow 1px difference for rounding


def test_normalize_image_preserves_aspect_ratio_portrait():
    """Test that portrait images preserve aspect ratio when downscaled."""
    test_image = create_test_image(width=1800, height=3200)
    normalized = normalize_image(test_image, max_dimension=2048)

    img = Image.open(io.BytesIO(normalized))
    # Height should be at max dimension
    assert img.height == 2048
    # Width should maintain aspect ratio
    expected_width = int(1800 * (2048 / 3200))
    assert abs(img.width - expected_width) <= 1  # Allow 1px difference for rounding
