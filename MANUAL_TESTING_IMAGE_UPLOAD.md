# Manual Testing Guide: Photo Upload Recipe Extraction

This guide provides step-by-step instructions for manually testing the photo upload recipe extraction feature.

## Prerequisites

1. Backend server running (development or production)
2. Valid JWT authentication token
3. Test image files (JPEG or PNG) containing recipe information

## Test Scenarios

### 1. Happy Path - Single Image Upload

**Objective**: Upload a single recipe photo and verify successful extraction.

**Steps**:

```bash
# 1. Get authentication token (login first)
TOKEN="your-jwt-token-here"

# 2. Create or use a test recipe image
# For testing, you can create a simple image with text using ImageMagick:
convert -size 800x600 -background white -fill black \
  -pointsize 24 -gravity center \
  label:"Test Recipe\n\nIngredients:\n- 2 cups flour\n- 1 cup sugar\n\nInstructions:\n1. Mix ingredients\n2. Bake at 350°F" \
  test_recipe.jpg

# 3. Upload the image
curl -X POST http://localhost:8000/api/v1/ai/extract-recipe-from-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@test_recipe.jpg"

# Expected Response (200 OK):
# {
#   "success": true,
#   "data": {
#     "draft_id": "uuid-here",
#     "signed_url": "/recipes/new?ai=1&draftId=uuid&token=jwt",
#     "expires_at": "2025-01-15T13:00:00Z",
#     "ttl_seconds": 3600
#   },
#   "message": "Recipe extracted successfully from image(s)"
# }
```

**Verification**:
- Response status is 200
- Response contains `draft_id`, `signed_url`, `expires_at`, and `ttl_seconds`
- `signed_url` can be used to navigate to the recipe form
- Draft is accessible via GET `/api/v1/ai/drafts/{draft_id}?token={token}`

---

### 2. Multi-File Upload

**Objective**: Upload multiple recipe pages in order.

**Steps**:

```bash
# Create multiple test images
convert -size 800x600 -background white -fill black \
  -pointsize 20 -gravity center \
  label:"Recipe Page 1\n\nTitle: Chocolate Cake\nPrep: 15 min\nCook: 30 min" \
  page1.jpg

convert -size 800x600 -background white -fill black \
  -pointsize 20 -gravity center \
  label:"Recipe Page 2\n\nIngredients:\n- 2 cups flour\n- 1 cup cocoa\n- 2 eggs" \
  page2.jpg

# Upload multiple files
curl -X POST http://localhost:8000/api/v1/ai/extract-recipe-from-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@page1.jpg" \
  -F "files=@page2.jpg"
```

**Verification**:
- Both images are processed
- Response is successful
- Extracted recipe combines information from both pages

---

### 3. Error: Unsupported Format

**Objective**: Verify rejection of non-JPEG/PNG files.

**Steps**:

```bash
# Create a GIF file
convert -size 800x600 -background white test.gif

# Try to upload
curl -X POST http://localhost:8000/api/v1/ai/extract-recipe-from-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@test.gif"

# Expected Response (415 Unsupported Media Type):
# {
#   "detail": "Unsupported image type: image/gif. Only image/jpeg, image/png are allowed."
# }
```

**Verification**:
- Response status is 415
- Error message indicates unsupported format

---

### 4. Error: File Too Large

**Objective**: Verify per-file size limit enforcement.

**Steps**:

```bash
# Create a large file (>8 MiB)
dd if=/dev/zero of=large.jpg bs=1M count=10

# Try to upload
curl -X POST http://localhost:8000/api/v1/ai/extract-recipe-from-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@large.jpg"

# Expected Response (413 Payload Too Large):
# {
#   "detail": "File size 10485760 bytes exceeds per-file limit of 8388608 bytes"
# }
```

**Verification**:
- Response status is 413
- Error message indicates size limit exceeded

---

### 5. Error: No Authentication

**Objective**: Verify authentication requirement.

**Steps**:

```bash
# Try to upload without token
curl -X POST http://localhost:8000/api/v1/ai/extract-recipe-from-image \
  -F "files=@test_recipe.jpg"

# Expected Response (401 Unauthorized):
# {
#   "detail": "Not authenticated"
# }
```

**Verification**:
- Response status is 401
- Authentication error message

---

### 6. Progress Streaming

**Objective**: Monitor extraction progress via SSE.

**Steps**:

```bash
# 1. First, upload an image to get draft_id
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/ai/extract-recipe-from-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@test_recipe.jpg")

DRAFT_ID=$(echo $RESPONSE | jq -r '.data.draft_id')

# 2. Subscribe to progress stream
curl -N http://localhost:8000/api/v1/ai/extract-recipe-image-stream?draft_id=$DRAFT_ID \
  -H "Authorization: Bearer $TOKEN"

# Expected: Server-Sent Events stream
# data: {"status":"complete","step":"complete","draft_id":"uuid","success":true,"progress":1.0}
```

**Verification**:
- SSE connection established
- Events received in text/event-stream format
- Final event indicates completion

---

### 7. Draft Retrieval

**Objective**: Fetch the created draft using signed token.

**Steps**:

```bash
# 1. Extract draft_id and token from upload response
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/ai/extract-recipe-from-image \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@test_recipe.jpg")

DRAFT_ID=$(echo $RESPONSE | jq -r '.data.draft_id')
SIGNED_URL=$(echo $RESPONSE | jq -r '.data.signed_url')
DRAFT_TOKEN=$(echo $SIGNED_URL | sed 's/.*token=//')

# 2. Fetch the draft
curl http://localhost:8000/api/v1/ai/drafts/$DRAFT_ID?token=$DRAFT_TOKEN

# Expected Response (200 OK):
# {
#   "success": true,
#   "data": {
#     "payload": {
#       "generated_recipe": { ... },
#       "extraction_metadata": { ... }
#     },
#     "type": "recipe_suggestion",
#     "created_at": "...",
#     "expires_at": "..."
#   }
# }
```

**Verification**:
- Draft is retrievable with signed token
- Payload contains extracted recipe data
- Type is "recipe_suggestion"

---

## Testing with Real Recipe Images

### Recommended Test Images

1. **Cookbook Page**: Clear printed recipe from a cookbook
2. **Recipe Card**: Index card with handwritten or typed recipe
3. **Screenshot**: Digital recipe from a website
4. **Photo**: Picture of a recipe from a book or magazine

### Image Quality Guidelines

For best results:
- Resolution: At least 800x600 pixels
- Format: JPEG or PNG
- Content: Clear, well-lit, minimal blur
- Text: Readable, not too small
- Orientation: Correct (will be auto-corrected via EXIF)

### Expected Extraction Quality

The AI extraction should successfully identify:
- ✅ Recipe title
- ✅ Ingredients with quantities and units
- ✅ Instructions (step by step)
- ✅ Prep time and cook time
- ✅ Servings
- ✅ Difficulty level
- ✅ Category (breakfast, lunch, dinner, etc.)

---

## Troubleshooting

### Issue: "Failed to process image"

**Cause**: Invalid image data or corrupted file

**Solution**: Verify the file is a valid JPEG/PNG image:
```bash
file test_recipe.jpg
# Should output: JPEG image data...
```

### Issue: "Combined file size exceeds limit"

**Cause**: Total size of all uploaded images > 20 MiB

**Solution**: Reduce number of files or compress images:
```bash
# Compress image with ImageMagick
convert input.jpg -quality 85 -resize 2048x2048\> output.jpg
```

### Issue: "No recipe found in image(s)"

**Cause**: AI could not identify recipe content in the image

**Solution**: 
- Ensure image contains clear recipe text
- Check image quality and readability
- Try with a different, clearer image

### Issue: Network timeout

**Cause**: Large image processing or slow AI response

**Solution**: 
- Use smaller images (under 2 MB recommended)
- Ensure proper JPEG compression
- Check backend logs for processing time

---

## Performance Benchmarks

Typical processing times:
- Image validation: < 10ms
- Image normalization: 50-200ms per image
- AI extraction: 2-4 seconds
- Draft creation: < 50ms
- **Total**: ~2-5 seconds end-to-end

Memory usage:
- Per request: ~10-30 MB (3x file size during processing)
- After request: Memory is freed (no image persistence)

---

## OpenAPI Documentation

The endpoints are documented in the interactive API docs:

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

Navigate to the "ai" tag to see the photo upload endpoints with request/response schemas.

---

## Next Steps

After successful testing:

1. **Frontend Integration**: Use the signed URL to navigate to the recipe form
2. **User Experience**: The form should be prefilled with extracted recipe data
3. **Error Handling**: Display appropriate error messages for different failure modes
4. **Progress Feedback**: Show loading state during extraction
5. **Success Confirmation**: Navigate to the prefilled form automatically

---

## Test Data Files

Sample test images can be generated using the commands above, or you can use:

- Real recipe photos from cookbooks
- Recipe cards
- Screenshots of online recipes
- Photos of printed recipes from magazines

Store test files in a separate directory (e.g., `test_data/recipes/`) and git-ignore them to avoid committing large binary files.
