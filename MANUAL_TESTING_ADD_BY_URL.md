# Manual Testing Guide: Add-by-URL Feature

This guide provides step-by-step instructions for manually testing the new "Add by URL" feature with streaming SSE support.

## Prerequisites

1. Backend service must be running with AI extraction endpoints enabled
2. Frontend dev server must be running
3. Valid recipe URLs for testing (examples below)

## Test Scenarios

### 1. Basic URL Extraction (Happy Path - Streaming)

**Objective**: Test the streaming SSE flow with a valid recipe URL

**Steps**:
1. Log in to the application
2. Navigate to `/recipes` page
3. Click the "Add by URL" button (secondary button next to "+ Add Recipe")
4. Enter a valid recipe URL (e.g., `https://www.allrecipes.com/recipe/...`)
5. Click "Extract Recipe"

**Expected Results**:
- Modal shows progress messages as events stream in:
  - "Starting extraction..."
  - "Fetching page content..."
  - "Analyzing recipe with AI..."
  - "Converting recipe data..."
  - "Recipe extracted successfully!"
- Browser navigates to `/recipes/new?ai=1&draftId=...&token=...`
- Form is pre-filled with extracted recipe data
- Blue AI indicator banner appears at top of form
- All fields (title, ingredients, instructions, etc.) are populated

### 2. Failed Extraction (No Recipe Found)

**Objective**: Test handling when AI cannot find a recipe on the page

**Steps**:
1. Log in and navigate to `/recipes`
2. Click "Add by URL"
3. Enter a URL that doesn't contain a recipe (e.g., search results page)
4. Click "Extract Recipe"

**Expected Results**:
- Progress messages appear during extraction
- Browser navigates to `/recipes/new?ai=1&draftId=...&token=...`
- Blue AI indicator banner appears (flag is set)
- Form is empty (no pre-filled data)
- No error is shown (just empty form state)

### 3. Fallback to POST (SSE Not Available)

**Objective**: Test POST fallback when SSE connection fails

**Steps**:
1. Use browser that doesn't support EventSource, or
2. Block SSE endpoint at network level
3. Log in and navigate to `/recipes`
4. Click "Add by URL" and enter valid recipe URL
5. Click "Extract Recipe"

**Expected Results**:
- Progress message shows "Switching to fallback method..."
- Single message: "Extracting recipe..."
- Browser navigates to signed URL on success
- Form is pre-filled correctly

### 4. Authentication Required

**Objective**: Test auth redirect for unauthenticated users

**Steps**:
1. Log out or use incognito mode
2. Manually navigate to: `/recipes/new?ai=1&draftId=test-123&token=test-jwt`

**Expected Results**:
- Browser redirects to `/login?next=/recipes/new?ai=1&draftId=test-123&token=test-jwt`
- After successful login, browser redirects back to the deep link
- Draft is fetched and form is pre-filled

### 5. Invalid URL Validation

**Objective**: Test client-side URL validation

**Steps**:
1. Log in and click "Add by URL"
2. Leave URL field empty and click "Extract Recipe"
3. Clear error and enter "not-a-url"
4. Click "Extract Recipe"

**Expected Results**:
- First case: Error message "Please enter a URL"
- Second case: Error message "Please enter a valid URL"
- No API call is made
- Modal remains open

### 6. Backend Error Handling

**Objective**: Test error display for backend failures

**Test Cases**:
- **422 Validation Error**: Submit URL with invalid format accepted by client but rejected by backend
- **500 Server Error**: AI model fails during extraction
- **401 Unauthorized**: Token expires during extraction

**Expected Results**:
- Error message displays in modal (red error banner)
- Modal remains open
- User can correct and retry
- No navigation occurs

### 7. Cancellation

**Objective**: Test canceling an in-progress extraction

**Steps**:
1. Log in and click "Add by URL"
2. Enter valid recipe URL
3. Click "Extract Recipe"
4. While progress messages are showing, click "Cancel"

**Expected Results**:
- SSE connection is closed
- Modal closes
- User remains on `/recipes` page
- No navigation occurs

### 8. Expired Token

**Objective**: Test handling of expired draft tokens in deep links

**Steps**:
1. Get a signed URL from a successful extraction
2. Wait for token to expire (default 1 hour)
3. Try to load the expired deep link URL

**Expected Results**:
- Error is logged in console
- Form is empty (no pre-filled data)
- User can manually enter recipe or try new URL

### 9. Form Edit After Prefill

**Objective**: Test that pre-filled form can be edited normally

**Steps**:
1. Successfully extract a recipe via URL
2. Verify form is pre-filled
3. Edit various fields (title, ingredients, instructions)
4. Save the recipe

**Expected Results**:
- All form fields are editable
- Changes are saved correctly
- Recipe appears in recipes list
- Original source URL is preserved in `link_source` field (if backend supports it)

### 10. Progress Messages Display

**Objective**: Test that streaming progress is visible and informative

**Steps**:
1. Log in and click "Add by URL"
2. Enter URL and start extraction
3. Observe progress messages

**Expected Results**:
- Progress area shows most recent 3 messages
- Messages are clear and descriptive
- Messages update smoothly without flashing
- Loading spinner is visible alongside messages

## Example Test URLs

### Valid Recipe URLs (for positive tests):
```
https://www.allrecipes.com/recipe/12345/example-recipe/
https://www.foodnetwork.com/recipes/...
https://cooking.nytimes.com/recipes/...
```

### Invalid URLs (for negative tests):
```
https://www.allrecipes.com/recipes/  (search page, no single recipe)
https://www.example.com/             (no recipe content)
https://www.amazon.com/              (completely unrelated)
```

## Validation Checklist

After each test scenario, verify:

- [ ] No JavaScript console errors
- [ ] No network request failures (check Network tab)
- [ ] Proper error messages shown to user
- [ ] Form state is correct (empty vs pre-filled)
- [ ] Navigation works as expected
- [ ] Back button behavior is correct
- [ ] Data is preserved correctly in store

## Performance Considerations

**Expected Timings**:
- SSE connection establishment: < 1 second
- Full extraction with streaming: 5-15 seconds typical
- POST fallback: 10-30 seconds (no progress updates)
- Draft fetch: < 500ms
- Form prefill: < 100ms

## Troubleshooting

### SSE Connection Issues
- Check browser console for EventSource errors
- Verify backend `/api/v1/ai/extract-recipe-stream` endpoint is accessible
- Check CORS settings if using different origins
- Verify cookie-based auth or query token auth is working

### Form Not Prefilling
- Check browser console for loader errors
- Verify draft fetch response structure matches expected schema
- Check that `setFormFromSuggestion()` is called in loader
- Verify useEffect dependencies in RecipesNewPage

### Navigation Not Working
- Check that signed_url is present in SSE complete event or POST response
- Verify navigate() is called with correct URL
- Check for JavaScript errors preventing navigation

## Browser Compatibility

Test in multiple browsers:
- [ ] Chrome/Chromium (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

Note: EventSource is supported in all modern browsers. IE11 is not supported.
