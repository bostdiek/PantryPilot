# AI Recipe Extraction Flow

This document explains the end-to-end flow for extracting a recipe from a URL, the shapes of success and failure responses, and how the frontend should handle each case.

## Overview

Endpoint: `POST /api/v1/ai/extract-recipe-from-url`
Retrieves and sanitizes HTML from a user-provided URL, invokes the AI extraction agent, persists the result as an `AIDraft`, and returns a **signed deep link** that the frontend can use to load the draft into the recipe creation page.

The endpoint ALWAYS returns HTTP 200 when the request is syntactically valid and authenticated, regardless of whether extraction succeeded, and signals outcome via the `success` boolean and `message` field. Hard failures (invalid URL, unauthorized, server errors) use appropriate non-200 status codes.

## Streaming Progress (Optional SSE Endpoint)

Endpoint: `GET /api/v1/ai/extract-recipe-stream?source_url=<url>&prompt_override=<optional>`

This endpoint streams Server‑Sent Events (SSE) so the frontend can show real‑time progress (spinner / step indicators) while the AI agent runs. Use when you want richer UX instead of a single blocking POST.

Each SSE message is sent as a `data:` line containing JSON followed by a blank line. Clients consume with the standard `EventSource` API. No custom event types are used (all are default `message`).

Event JSON schema (keys omitted when not applicable):

```jsonc
{
  "status": "started|fetching|sanitizing|ai_call|converting|complete|error",
  "step": "<string>",            // machine friendly step id
  "detail": "<string|null>",     // human readable message (optional)
  "progress": 0.0,                // coarse progress (0.0–1.0) or null
  "draft_id": "<uuid>",          // only in final complete/error when a draft was persisted
  "signed_url": "/recipes/new?...", // deep link (complete event only)
  "success": true,                // only on final event (true|false)
  "confidence_score": 0.82        // only on success
}
```

Example frontend usage:

```ts
const es = new EventSource(`/api/v1/ai/extract-recipe-stream?source_url=${encodeURIComponent(url)}`);
es.onmessage = (evt) => {
  const data = JSON.parse(evt.data);
  switch (data.status) {
    case 'started': /* init UI */ break;
    case 'fetching': /* show network fetch */ break;
    case 'ai_call': /* show model running */ break;
    case 'converting': /* show assembling result */ break;
    case 'complete': {
      es.close();
      // Navigate immediately using signed_url regardless of success flag
      if (data.signed_url) router.push(data.signed_url);
      break;
    }
    case 'error': {
      es.close();
      toast.error(data.detail || 'Extraction failed');
      break;
    }
  }
};
es.onerror = () => {
  es.close();
  toast.error('Connection lost during extraction');
};
```

Recommended UX pattern:

1. User submits URL.
1. Open SSE connection immediately; disable form / show progress steps.
1. On `complete` or terminal `error`, navigate (if `signed_url`) or surface retry UI.
1. Fallback: If the SSE connection errors early, you can optionally fall back to the POST endpoint.

Choosing between POST vs. SSE:

| Criterion                | POST (existing)            | SSE (new)                             |
|--------------------------|----------------------------|---------------------------------------|
| Implementation effort    | Already done               | Slightly more (stream parsing)        |
| User feedback            | Spinner only               | Step-by-step progress                 |
| Network compatibility    | Broad                      | Broad (HTTP/1.1 keep-alive)           |
| Cancellation             | Hard (must abort request)  | Close EventSource to cancel early     |
| Future extensibility     | Limited                    | Can add retries / incremental events  |

Both endpoints end with a draft + deep link; frontend handling post-navigation stays identical.

## Response Patterns

### 1. Successful Extraction

````http
POST /api/v1/ai/extract-recipe-from-url
{
  "source_url": "https://example.com/valid-recipe"
}

Response (HTTP 200):

```json
{
  "success": true,
  "data": {
    "draft_id": "<uuid>",
    "signed_url": "/recipes/new?ai=1&draftId=<uuid>&token=<jwt>",
    "expires_at": "2025-10-03T20:03:34.543240Z",
    "ttl_seconds": 3600
  },
  "message": "Recipe extracted successfully",
  "error": null
}
````

### 2. Extraction Failure (No Recipe Found / Non-recipe Page)

````http
POST /api/v1/ai/extract-recipe-from-url
{
  "source_url": "https://example.com/search-results"
}

Response (HTTP 200, `success=false`):

```json
{
  "success": false,
  "data": {
    "draft_id": "<uuid>",
    "signed_url": "/recipes/new?ai=1&draftId=<uuid>&token=<jwt>",
    "expires_at": "2025-10-03T20:09:26.442693Z",
    "ttl_seconds": 3600
  },
  "message": "Recipe extraction failed: <reason>",
  "error": null
}
````

A draft is still created so the frontend has a uniform deep-link mechanism. The draft payload contains structured failure metadata (see below).

### 3. Validation / Auth Errors (Examples)

| Scenario                             | Status | Example                                                         |
| ------------------------------------ | ------ | --------------------------------------------------------------- |
| Invalid URL format                   | 422    | `{"detail": "..."}`                                             |
| Unauthorized (missing/invalid token) | 401    | `{"detail": "Not authenticated"}`                               |
| Internal AI error                    | 500    | Standard error envelope with `success=false` and `error` object |

## Draft Retrieval

Endpoint: `GET /api/v1/ai/drafts/{draft_id}?token=<jwt>`

On success (HTTP 200):

```json
{
  "success": true,
  "data": {
    "payload": {
      "generated_recipe": { ... } | null,
      "extraction_metadata": {
        "confidence_score": 0.87,              # success only
        "source_url": "https://example.com/...",
        "extracted_at": "2025-10-03T19:03:34.543173+00:00",
        "failure": {                           # present ONLY when extraction failed
          "reason": "No recipe found..."
        }
      }
    },
    "type": "recipe_suggestion",
    "created_at": "...",
    "expires_at": "..."
  },
  "message": "...",
  "error": null
}
```

## Draft Payload Schema

```json
payload = {
  "generated_recipe": {            # Present when success; null on failure
     "recipe_data": { ... RecipeCreate fields ... },
     "confidence_score": <float>,
     "extraction_notes": null | string,
     "source_url": "..."
  } | null,
  "extraction_metadata": {
     "confidence_score": <float>,  # success only (0.0 if omitted)
     "source_url": "...",         # original URL
     "extracted_at": "<iso8601>",
     "failure": {                  # included only on failure
        "reason": "<string>"
     }
  }
}
```

## Frontend Handling Logic

Pseudo-flow when user submits a URL:

1. `POST /ai/extract-recipe-from-url` with `{ source_url }`.
1. If HTTP != 200: show error toast (network/validation/auth) and stop.
1. If HTTP 200:

- Store `data.draft_id`, `signed_url`, `expires_at`.
- Navigate to `signed_url` (or push route using the embedded params) regardless of `success`.

1. On recipe creation page mount, call `GET /ai/drafts/{draft_id}?token=<token>`.
1. Inspect `data.payload`:

- If `generated_recipe` is not null: pre-fill form fields with `recipe_data`.
- If `generated_recipe` is null AND `extraction_metadata.failure` exists:
  - Show inline extraction failure banner with `failure.reason`.
  - Provide actions: Retry with different URL, Edit manually (empty form), or Dismiss.

1. Expiry Handling:

- If draft fetch returns 404 (expired), show message and prompt re-extraction.

## UI Recommendations

- Distinguish three states in the recipe creation UI: `loading`, `extracted`, `extraction_failed`.
- Show confidence score (e.g., badge) when available; optionally warn when < 0.6.
- Log failure reasons for analytics (e.g., categorize: no_recipe_found, timeout, malformed_html).

## Rationale: Why Create a Draft on Failure?

Creating a draft even on failure yields a single, consistent deep link flow. The frontend does not need branching logic before routing; instead, it inspects the draft payload. This simplifies optimistic navigation and allows persisted failure context (useful for user retry UX and analytics).

## Edge Cases & Notes

- Ingredient normalization has been removed; ingredient name & prep are now passed through verbatim from the AI output (no splitting / mutation).
- If the user overrides the system prompt (`prompt_override`), store & surface this (future enhancement: show in UI for transparency).
- Future extension: partial extraction (e.g., only ingredients found). Current model: either recipe fields or failure – but frontend should tolerate missing optional fields.

## Versioning & Stability

- This flow is considered beta; structure may evolve. Wrap accesses defensively (null checks) and prefer feature detection (`failure` key) instead of strict schema positional assumptions.

## Quick Reference Decision Table

| Condition | generated_recipe | failure key | UI State          |
| --------- | ---------------- | ----------- | ----------------- |
| Success   | object           | absent      | extracted         |
| Failure   | null             | present     | extraction_failed |

---

Last updated: 2025-10-04 (added SSE streaming endpoint docs & normalization note update)
