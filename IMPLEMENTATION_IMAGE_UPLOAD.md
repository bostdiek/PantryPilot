# Photo Upload OCR → AI Draft Implementation

## Overview

This document describes the implementation of the photo upload recipe extraction feature, which allows users to upload images of recipes (from cookbooks, recipe cards, or handwritten notes) and extract structured recipe data using AI.

## Architecture

The implementation follows the existing draft + signed deep-link pattern used by URL-based imports (see `docs/adr/` for contract and deep-link ADRs).

### Key Components

1. **Image Normalization Service** (`services/images/normalize.py`)
   - Validates image format (JPEG/PNG only)
   - Enforces file size limits (8 MiB per file, 20 MiB combined)
   - Normalizes images using Pillow:
     - Applies EXIF orientation correction
     - Converts to RGB color space
     - Downscales to max 2048px dimension
     - Re-encodes to JPEG with quality=85

2. **AI Agent** (`services/ai/agents.py`)
   - Added `create_image_recipe_agent()` function
   - Uses Gemini Flash multimodal capabilities
   - Dedicated system prompt for image-based extraction

3. **API Endpoints** (`api/v1/ai.py`)
   - `POST /api/v1/ai/extract-recipe-from-image`: Main upload endpoint
   - `GET /api/v1/ai/extract-recipe-image-stream`: Progress streaming endpoint

## API Contract

### POST /api/v1/ai/extract-recipe-from-image

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Authentication: Required (JWT Bearer token)
- Fields:
  - `files`: One or more image files (repeated field for multiple files)

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "draft_id": "uuid",
    "signed_url": "/recipes/new?ai=1&draftId=uuid&token=jwt",
    "expires_at": "2025-01-15T12:00:00Z",
    "ttl_seconds": 3600
  },
  "message": "Recipe extracted successfully from image(s)"
}
```

**Error Responses:**
- 401: Unauthorized (missing/invalid JWT)
- 413: Payload Too Large (file size exceeds limits)
- 415: Unsupported Media Type (not JPEG/PNG)
- 422: Unprocessable Entity (no files or invalid format)
- 500: Internal Server Error (unexpected failures)

### GET /api/v1/ai/extract-recipe-image-stream

**Request:**
- Method: GET
- Query Parameters:
  - `draft_id`: UUID of the draft to monitor
- Authentication: Required (JWT Bearer token)

**Response:**
- Content-Type: text/event-stream
- Server-Sent Events with progress updates

## Implementation Details

### File Size Limits

Configuration constants in `services/images/normalize.py`:
- `PER_FILE_SIZE_LIMIT`: 8 MiB (8 * 1024 * 1024 bytes)
- `COMBINED_SIZE_LIMIT`: 20 MiB (20 * 1024 * 1024 bytes)
- `MAX_IMAGE_DIMENSION`: 2048 pixels
- `JPEG_QUALITY`: 85

### Image Processing Pipeline

1. **Upload & Validation**
   - Receive multipart form data
   - Read files into memory
   - Validate content types
   - Check file sizes

2. **Normalization**
   - Open with PIL/Pillow
   - Apply EXIF orientation
   - Convert to RGB (handles RGBA with white background)
   - Downscale if needed (preserving aspect ratio)
   - Re-encode to JPEG

3. **AI Extraction**
   - Create image recipe agent
   - Convert images to base64 data URLs
   - Call Gemini Flash with images
   - Parse extraction result

4. **Draft Creation**
   - Convert extraction to RecipeCreate schema
   - Create AIDraft in database (TTL = 1 hour)
   - Generate signed token
   - Return response with deep link

### Multi-File Support

- Accepts multiple files via repeated `files` field
- Processes files in order provided by client
- Validates each file independently
- Normalizes all files before AI extraction
- Future enhancement: Merge multi-page extractions

### Security & Privacy

- Authentication required via `get_current_user()` dependency
- Signed deep-link tokens scoped to draft_id and owner
- Images kept in memory only (not persisted to disk)
- Normalized images passed directly to AI (no intermediate storage)

## Testing

### Image Normalization Tests (`tests/test_image_normalize.py`)

17 unit tests covering:
- Content type validation (JPEG/PNG/invalid)
- File size validation (per-file and combined limits)
- Image normalization (EXIF, RGB conversion, downscaling)
- RGBA to RGB conversion with white background
- Aspect ratio preservation
- Invalid image data handling

Coverage: 97% (68/70 statements)

### API Integration Tests (`tests/ai/test_api_extract_image.py`)

8 integration tests covering:
- Happy path (single and multiple files)
- Authentication requirement
- Invalid format rejection (415)
- File size limit enforcement (413)
- Empty file list handling (422)
- Extraction not found scenario
- Multi-file upload

Coverage: 51% of endpoint code (focuses on critical paths)

## Future Enhancements

### Phase 1 (Current Implementation)
- ✅ Single/multi-file upload
- ✅ Image validation and normalization
- ✅ Basic multimodal AI extraction
- ✅ Draft creation and signed deep links

### Phase 2 (Planned)
- [ ] Full Gemini multimodal API integration (currently simplified)
- [ ] Background async processing for large uploads
- [ ] Streaming progress updates during extraction
- [ ] OCR fallback (Tesseract) for unreliable extractions
- [ ] Near-duplicate page detection
- [ ] Page order optimization hints

### Phase 3 (Future)
- [ ] Image preprocessing (contrast, brightness adjustment)
- [ ] Multi-language OCR support
- [ ] Handwriting recognition improvements
- [ ] Recipe photo collage support

## Dependencies

### Added
- `pillow>=11.3.0`: Image processing library

### Existing
- `pydantic-ai>=1.0.10`: AI agent framework
- `google-generativeai>=0.8.5`: Gemini API access
- `fastapi[standard]>=0.116.1`: Web framework

## Performance Considerations

- Image normalization: ~50-200ms per image (depending on size)
- JPEG re-encoding reduces file size by 30-70% typically
- Base64 encoding adds ~33% to payload size for AI
- Full extraction pipeline: ~2-5 seconds per request
- Memory usage: ~3x original file size during processing

## Monitoring & Metrics

Recommended metrics to track:
- Upload success rate
- File size distribution
- Extraction success rate
- Processing time (p50, p95, p99)
- Error rate by type (413, 415, 422, 500)

## Deployment Notes

- No database migrations required (reuses existing AIDraft table)
- No environment variables required (uses existing AI config)
- Compatible with existing frontend contract
- Backward compatible with URL-based extraction

## Known Limitations

1. **Multimodal Integration**: Current implementation uses simplified agent call. Full Gemini multimodal support requires API enhancement.

2. **Synchronous Processing**: Extraction happens synchronously during POST request. Consider background tasks for production with large images.

3. **No Image Storage**: Images are not persisted. Users must re-upload to retry extraction.

4. **Single Recipe Per Upload**: Currently extracts one recipe from all images combined. Future enhancement needed for multi-recipe detection.

## Related Documentation

- `docs/adr/2025-09-11-deep-links-for-ai-drafts.md`: Deep link contract
- `BACKEND_TUTORIAL.md`: Backend development guide
- `.github/instructions/backend-python-fastapi.instructions.md`: Coding standards
