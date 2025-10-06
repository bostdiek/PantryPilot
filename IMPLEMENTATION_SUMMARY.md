# Add-by-URL Feature Implementation Summary

## Overview

This document summarizes the implementation of the "Add by URL" feature with streaming Server-Sent Events (SSE) support for extracting recipes from URLs using AI.

## Key Features

1. **Streaming-first approach**: Uses SSE for real-time progress updates during AI extraction
2. **Fallback mechanism**: Automatically falls back to POST endpoint if SSE fails
3. **Deep link prefill**: Signed URLs enable form pre-filling from AI-extracted drafts
4. **Authentication aware**: Redirects unauthenticated users to login with return URL
5. **Error handling**: Comprehensive error states with user-friendly messages

## Architecture

### Frontend Components

#### 1. API Layer (`apps/frontend/src/api/endpoints/aiDrafts.ts`)

**Purpose**: Communicate with backend AI extraction endpoints

**Key Functions**:
- `extractRecipeStream()`: SSE streaming extraction (preferred method)
- `extractRecipeFromUrl()`: POST fallback for non-streaming environments
- `getDraftById()`: Fetch draft using signed token (public route)
- `getDraftByIdOwner()`: Fetch draft for authenticated owner (protected route)

**SSE Implementation**:
```typescript
const eventSource = new EventSource(url, { withCredentials: true });
eventSource.onmessage = (evt) => {
  const data = JSON.parse(evt.data) as SSEEvent;
  // Handle progress, complete, error events
};
```

**Features**:
- Cookie-based authentication for SSE (EventSource limitation)
- Progress callbacks for UI updates
- Automatic cleanup on completion/error
- Type-safe event parsing

#### 2. Types (`apps/frontend/src/types/AIDraft.ts`)

**Purpose**: TypeScript interfaces matching backend schemas

**Key Types**:
- `AIDraftPayload`: Complete draft structure with recipe and metadata
- `AIGeneratedRecipe`: Extracted recipe data with confidence score
- `AIDraftResponse`: Response from extraction endpoints
- `SSEEvent`: Streaming event structure

**Design**: Mirrors backend Pydantic schemas for type safety

#### 3. Store Updates (`apps/frontend/src/stores/useRecipeStore.ts`)

**Purpose**: Manage AI suggestion state for form prefilling

**New State**:
- `formSuggestion: RecipeCreate | null`: Stores the AI-extracted recipe data
- `isAISuggestion: boolean`: Flag indicating AI-generated content

**New Actions**:
- `setFormFromSuggestion(payload)`: Parse draft payload and store recipe data
- `clearFormSuggestion()`: Reset suggestion state

**Usage Pattern**:
```typescript
// In route loader
const draftResponse = await getDraftById(draftId, token);
setFormFromSuggestion(draftResponse.payload);

// In component
useEffect(() => {
  if (formSuggestion) {
    // Prefill form fields
    clearFormSuggestion(); // Prevent re-runs
  }
}, [formSuggestion]);
```

#### 4. UI Components

**AddByUrlModal (`apps/frontend/src/components/recipes/AddByUrlModal.tsx`)**:
- URL input with client-side validation
- Streaming progress display (last 3 messages)
- Loading states and error handling
- Cancel functionality

**RecipesPage Updates**:
- New "Add by URL" button (secondary variant)
- Modal integration

**RecipesNewPage Updates**:
- AI indicator banner (blue info box)
- useEffect to prefill form from suggestion
- No changes to save/submit logic

#### 5. Router Configuration (`apps/frontend/src/routerConfig.tsx`)

**New Loader**: `newRecipeLoader`

**Responsibilities**:
1. Parse query params: `?ai=1&draftId=...&token=...`
2. Check authentication, redirect if needed
3. Fetch draft using signed token
4. Call `setFormFromSuggestion()` to populate store
5. Handle errors gracefully (no throws)

**Auth Flow**:
```typescript
if (!authToken) {
  return redirect(`/login?next=${encodeURIComponent(fullUrl)}`);
}
```

### Backend Integration Points

#### Endpoints Used

1. **POST `/api/v1/ai/extract-recipe-from-url`**
   - Request: `{ source_url, prompt_override? }`
   - Response: `{ draft_id, signed_url, expires_at, ttl_seconds }`
   - Auth: Bearer token required

2. **GET `/api/v1/ai/extract-recipe-stream`**
   - Query params: `?source_url=...&prompt_override=...`
   - Response: Server-Sent Events stream
   - Auth: Cookie-based (EventSource limitation)
   - Events: started, fetching, ai_call, converting, complete, error

3. **GET `/api/v1/ai/drafts/{draft_id}`**
   - Query params: `?token=<signed-jwt>`
   - Response: Draft payload with recipe data or failure info
   - Auth: None (public route, token in query)

4. **GET `/api/v1/ai/drafts/{draft_id}/me`**
   - Response: Same as above
   - Auth: Bearer token required (owner-only)

#### Expected Backend Behavior

**Successful Extraction**:
```json
{
  "payload": {
    "generated_recipe": {
      "recipe_data": { /* RecipeCreate fields */ },
      "confidence_score": 0.9,
      "source_url": "..."
    },
    "extraction_metadata": {
      "source_url": "...",
      "extracted_at": "...",
      "confidence_score": 0.9
    }
  }
}
```

**Failed Extraction**:
```json
{
  "payload": {
    "generated_recipe": null,
    "extraction_metadata": {
      "source_url": "...",
      "failure": {
        "reason": "No recipe found"
      }
    }
  }
}
```

## Data Flow

### Streaming Extraction Flow

```
User clicks "Add by URL"
    ↓
Modal opens with URL input
    ↓
User enters URL and clicks "Extract Recipe"
    ↓
Frontend establishes SSE connection
    ↓
Backend streams progress events:
  - started
  - fetching (HTML fetch)
  - ai_call (AI processing)
  - converting (data conversion)
  - complete (with signed_url)
    ↓
Frontend receives complete event with signed_url
    ↓
Navigate to /recipes/new?ai=1&draftId=...&token=...
    ↓
Route loader detects AI params
    ↓
Fetch draft using token
    ↓
Call setFormFromSuggestion(payload)
    ↓
Component useEffect prefills form
    ↓
User reviews/edits and saves
```

### Fallback POST Flow

```
SSE connection fails
    ↓
Catch error in onError handler
    ↓
Call fallbackToPost()
    ↓
POST to /api/v1/ai/extract-recipe-from-url
    ↓
Wait for response (no progress updates)
    ↓
Receive { draft_id, signed_url, ... }
    ↓
Navigate to signed_url
    ↓
[Rest same as streaming flow]
```

## Testing

### Test Coverage

**API Endpoint Tests** (`aiDrafts.test.ts`):
- ✅ POST extraction with/without prompt_override
- ✅ SSE connection establishment and URL encoding
- ✅ SSE progress, complete, and error event handling
- ✅ SSE connection errors and fallback triggers
- ✅ Draft fetch with valid/expired tokens
- ✅ Owner-only draft fetch

**Store Tests** (`useRecipeStore.aiSuggestion.test.ts`):
- ✅ setFormFromSuggestion with valid recipe data
- ✅ setFormFromSuggestion with failed extraction (null recipe)
- ✅ setFormFromSuggestion with all optional fields
- ✅ clearFormSuggestion behavior
- ✅ Integration with existing store state

**Build Validation**:
- ✅ TypeScript compilation
- ✅ ESLint passing
- ✅ All 322 tests passing
- ✅ Production build successful

### Manual Testing Required

See `MANUAL_TESTING_ADD_BY_URL.md` for comprehensive manual test scenarios:
1. Basic streaming extraction (happy path)
2. Failed extraction handling
3. POST fallback behavior
4. Authentication redirect
5. URL validation
6. Error handling (422, 500, 401)
7. Cancellation
8. Expired tokens
9. Form editing after prefill
10. Progress message display

## Security Considerations

1. **Signed Tokens**: Deep links use JWT tokens with expiration (default 1h)
2. **Token Validation**: Backend validates token signature and expiration
3. **Auth Redirect**: Unauthenticated users must log in before accessing drafts
4. **No Autosave**: Loader only reads data, no mutations
5. **SSRF Protection**: Backend validates URLs (not frontend's responsibility)
6. **XSS Prevention**: All user input is sanitized by React

## Performance

**Expected Timings**:
- SSE connection: < 1s
- Full streaming extraction: 5-15s
- POST fallback: 10-30s
- Draft fetch: < 500ms
- Form prefill: < 100ms

**Optimizations**:
- Streaming provides early feedback
- Draft caching in store (future enhancement)
- Lazy loading of modal component (already implemented)

## Error Handling

### User-Facing Errors

| Scenario | Display | Action |
|----------|---------|--------|
| Invalid URL (client) | Modal error: "Please enter a valid URL" | User corrects URL |
| Backend 422 | Modal error: "Invalid URL format" | User tries different URL |
| Backend 500 | Modal error: "Failed to extract recipe" | User can retry |
| SSE failure | Switch to POST fallback | Transparent to user |
| Expired token | Form empty, log warning | User tries new extraction |
| Not authenticated | Redirect to login | User logs in, returns |

### Developer/Console Errors

- Logged but not shown to user
- Include correlation IDs where available
- Preserve error context for debugging

## Future Enhancements

1. **Retry Logic**: Automatic retries for transient failures
2. **Draft History**: View past extractions
3. **Confidence Threshold**: Warn user if confidence score < threshold
4. **Progress Bar**: Visual progress indicator (0-100%)
5. **Preview Mode**: Show extraction before navigating
6. **Batch Import**: Multiple URLs at once
7. **Browser Extension**: Right-click on recipe pages

## Known Limitations

1. **EventSource Headers**: Cannot set Authorization header; requires cookie-based auth or query token
2. **No Cancel Signal**: EventSource doesn't support AbortController (use close())
3. **Browser Support**: IE11 not supported (EventSource unavailable)
4. **Token Lifetime**: 1 hour default; stale links won't work

## Documentation

- **User Guide**: To be created
- **API Documentation**: Backend OpenAPI docs at `/api/v1/docs`
- **ADRs Referenced**:
  - `docs/adr/2025-09-11-ai-suggestion-contracts.md`
  - `docs/adr/2025-09-11-deep-links-for-ai-drafts.md`
  - `docs/adr/2025-09-11-unified-ai-suggestions-deep-links.md`
- **Backend Flow**: `docs/AI_RECIPE_EXTRACTION_FLOW.md`

## Files Changed

### New Files (7)
1. `apps/frontend/src/types/AIDraft.ts`
2. `apps/frontend/src/api/endpoints/aiDrafts.ts`
3. `apps/frontend/src/components/recipes/AddByUrlModal.tsx`
4. `apps/frontend/src/api/endpoints/__tests__/aiDrafts.test.ts`
5. `apps/frontend/src/stores/__tests__/useRecipeStore.aiSuggestion.test.ts`
6. `MANUAL_TESTING_ADD_BY_URL.md`
7. `IMPLEMENTATION_SUMMARY.md` (this file)

### Modified Files (5)
1. `apps/frontend/src/stores/useRecipeStore.ts` (+35 lines)
2. `apps/frontend/src/pages/RecipesPage.tsx` (+10 lines)
3. `apps/frontend/src/pages/RecipesNewPage.tsx` (+50 lines)
4. `apps/frontend/src/routerConfig.tsx` (+45 lines)
5. `apps/frontend/package-lock.json` (dependency updates)

## Deployment Notes

1. **Backend Dependency**: Requires backend AI extraction endpoints deployed
2. **Environment Variables**: Verify `VITE_API_URL` in production
3. **CORS Configuration**: Ensure SSE endpoint allows credentials
4. **Token Signing**: Backend must use consistent JWT secret
5. **Monitoring**: Track SSE connection success rate and extraction duration

## Support and Maintenance

**Contact**: See repository maintainers
**Issues**: GitHub Issues for bug reports
**Contributing**: Follow contribution guidelines in CONTRIBUTING.md
