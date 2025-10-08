"""Image normalization utilities for recipe photo uploads.

This module provides utilities to validate, normalize, and prepare images
for AI multimodal extraction. It handles EXIF orientation, color space
conversion, downscaling, and re-encoding to optimize images for processing.
"""

import io
import logging

from PIL import Image, ImageOps
from PIL.Image import Image as PILImage


logger = logging.getLogger(__name__)

# Configuration constants
MAX_IMAGE_DIMENSION = 2048  # Maximum width or height in pixels
JPEG_QUALITY = 85  # JPEG re-encoding quality (0-100)
PER_FILE_SIZE_LIMIT = 8 * 1024 * 1024  # 8 MiB per file
COMBINED_SIZE_LIMIT = 20 * 1024 * 1024  # 20 MiB total

# Allowed MIME types
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}


class ImageValidationError(Exception):
    """Raised when image validation fails."""

    pass


class ImageSizeLimitError(ImageValidationError):
    """Raised when image size exceeds limits."""

    pass


class ImageFormatError(ImageValidationError):
    """Raised when image format is not supported."""

    pass


def validate_content_type(content_type: str) -> None:
    """Validate that the content type is an allowed image format.

    Args:
        content_type: The MIME type of the uploaded file

    Raises:
        ImageFormatError: If content type is not allowed
    """
    if content_type not in ALLOWED_MIME_TYPES:
        raise ImageFormatError(
            f"Unsupported image type: {content_type}. "
            f"Only {', '.join(ALLOWED_MIME_TYPES)} are allowed."
        )


def validate_file_size(size: int, per_file_limit: int = PER_FILE_SIZE_LIMIT) -> None:
    """Validate that a file size is within the per-file limit.

    Args:
        size: Size of the file in bytes
        per_file_limit: Maximum allowed size per file in bytes

    Raises:
        ImageSizeLimitError: If file size exceeds the limit
    """
    if size > per_file_limit:
        raise ImageSizeLimitError(
            f"File size {size} bytes exceeds per-file limit of {per_file_limit} bytes"
        )


def validate_combined_size(
    sizes: list[int], combined_limit: int = COMBINED_SIZE_LIMIT
) -> None:
    """Validate that combined file sizes are within the total limit.

    Args:
        sizes: List of file sizes in bytes
        combined_limit: Maximum allowed combined size in bytes

    Raises:
        ImageSizeLimitError: If combined size exceeds the limit
    """
    total = sum(sizes)
    if total > combined_limit:
        raise ImageSizeLimitError(
            f"Combined file size {total} bytes exceeds limit of {combined_limit} bytes"
        )


def normalize_image(
    image_bytes: bytes,
    max_dimension: int = MAX_IMAGE_DIMENSION,
    jpeg_quality: int = JPEG_QUALITY,
) -> bytes:
    """Normalize an image for AI processing.

    Performs the following operations:
    1. Opens the image and applies EXIF orientation
    2. Converts to RGB color space
    3. Downscales to max dimension preserving aspect ratio
    4. Re-encodes to JPEG format

    Args:
        image_bytes: Raw image data
        max_dimension: Maximum width or height in pixels
        jpeg_quality: JPEG encoding quality (0-100)

    Returns:
        Normalized image as JPEG bytes

    Raises:
        ImageValidationError: If image cannot be processed
    """
    try:
        # Open image from bytes
        image: PILImage = Image.open(io.BytesIO(image_bytes))

        # Apply EXIF orientation if present
        image = ImageOps.exif_transpose(image)

        # Convert to RGB (handles RGBA, grayscale, etc.)
        if image.mode != "RGB":
            # For images with transparency, use white background
            if image.mode in ("RGBA", "LA", "PA"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.split()[-1])  # Use alpha as mask
                image = background
            else:
                image = image.convert("RGB")

        # Downscale if needed, preserving aspect ratio
        width, height = image.size
        if width > max_dimension or height > max_dimension:
            # Calculate new dimensions
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))

            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.debug(
                "Downscaled image from %dx%d to %dx%d",
                width,
                height,
                new_width,
                new_height,
            )

        # Re-encode to JPEG
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=jpeg_quality, optimize=True)
        normalized_bytes = output.getvalue()

        logger.debug(
            "Normalized image: original=%d bytes, normalized=%d bytes",
            len(image_bytes),
            len(normalized_bytes),
        )

        return normalized_bytes

    except Exception as e:
        logger.error("Failed to normalize image: %s", e)
        raise ImageValidationError(f"Failed to process image: {e}") from e


def normalize_images(
    image_files: list[tuple[bytes, str]],
    max_dimension: int = MAX_IMAGE_DIMENSION,
    jpeg_quality: int = JPEG_QUALITY,
) -> list[bytes]:
    """Normalize multiple images for AI processing.

    Args:
        image_files: List of (image_bytes, content_type) tuples
        max_dimension: Maximum width or height in pixels
        jpeg_quality: JPEG encoding quality (0-100)

    Returns:
        List of normalized image bytes in the same order

    Raises:
        ImageValidationError: If validation or normalization fails
    """
    # Validate all files first
    sizes = []
    for image_bytes, content_type in image_files:
        validate_content_type(content_type)
        size = len(image_bytes)
        validate_file_size(size)
        sizes.append(size)

    validate_combined_size(sizes)

    # Normalize all images
    normalized = []
    for image_bytes, _ in image_files:
        normalized_bytes = normalize_image(image_bytes, max_dimension, jpeg_quality)
        normalized.append(normalized_bytes)

    return normalized
