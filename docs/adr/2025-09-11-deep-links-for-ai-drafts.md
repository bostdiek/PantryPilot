# Signed Deep Links for AI Drafts and Intents

## Status
Proposed

## Context
PantryPilot's AI-assisted features allow authenticated users to generate drafts for recipes and meal plans via API calls (POST /api/v1/ai-drafts/recipes, /api/v1/ai-drafts/mealplans). The server validates, stores the draft, and returns a draftId along with a short-lived, signed deep link. The frontend must support linkable routes that parse intent parameters (e.g., ai=1, draftId) to fetch and pre-fill the UI without triggering mutations on load. Explicit user confirmation is required for any changes.

Key requirements:
- Deep link patterns: /recipes/new?ai=1&prompt=TEXT (opens AI panel, pre-fills prompt); /mealplan?ai=fill-week&weekStart=YYYY-MM-DD (opens AI panel for week fill).
- Router must parse and expose intent params; existing non-AI flows unchanged.
- Authentication required for protected intents; unauthenticated users redirect to /login?next=FULL_DEEP_LINK.
- If draftId present, fetch draft via GET; invalid/expired shows friendly error with "Start New" option.
- Drafts have TTL (e.g., 1 hour) and strict validation; links signed and short-lived.
- No sensitive data in query params; limit URL payload size. Prefer server-stored drafts over fragments (#payload=).
- Deep links cause no side effects; only read/pre-fill on load.

This decision builds on existing auth (JWT in core/security.py), schemas (src/schemas/), models (users.py, recipes.py, mealplans.py), backend endpoints (api/v1/recipes.py, mealplans.py), and frontend routing (routerConfig.tsx), API hooks (useApi.ts), auth store (useAuthStore.ts).

## Decision

### Contracts
New schemas in `src/schemas/ai_drafts.py`:

- **AIDraftCreate** (request body for POST):
  ```python
  from pydantic import BaseModel, Field
  from typing import Optional, Dict, Any, Literal
  from datetime import datetime
  from uuid import UUID

  class AIDraftCreate(BaseModel):
      prompt: str = Field(..., max_length=1000, description="AI generation prompt")
      params: Optional[Dict[str, Any]] = Field(None, description="Intent-specific params, e.g., {'weekStart': '2025-09-15'}")

  class AIDraftResponse(BaseModel):
      draft_id: UUID
      signed_url: str  # e.g., /recipes/new?ai=1&draftId=uuid&token=signed_jwt
      expires_at: datetime  # TTL info for UI

  class AIDraftFetchResponse(BaseModel):
      payload: Dict[str, Any]  # Stored draft data, e.g., {'title': 'AI Recipe', 'ingredients': [...]}
      type: Literal['recipe', 'mealplan']
  ```

- Endpoints:
  - POST `/api/v1/ai-drafts/{draft_type}` (draft_type: 'recipes' | 'mealplans'): Create draft, store in DB, sign JWT with {draft_id, exp (now+1h), type}, return AIDraftResponse. Requires auth via get_current_user.
  - GET `/api/v1/ai-drafts/{draft_id}`: Decode/validate signed token from query, check exp/user_id, return AIDraftFetchResponse if valid. Raises 401/404 on invalid/expired.

- Signed URL format: Append to base route, e.g., base64url(JWT payload: {"draft_id": uuid, "exp": timestamp, "type": "recipe"}) as query param 'token'. Use existing create_access_token (adapt for draft, no sub=user_id but include user_id for validation).

- DB Model: New `AIDraft` in `src/models/ai_drafts.py`:
  ```python
  from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
  from sqlalchemy.dialects.postgresql import UUID as PG_UUID
  from .base import Base
  import uuid

  class AIDraft(Base):
      __tablename__ = "ai_drafts"
      id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
      type = Column(String(20), nullable=False)  # 'recipe' | 'mealplan'
      payload = Column(JSON, nullable=False)  # Draft data as JSON
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      expires_at = Column(DateTime(timezone=True), nullable=False)  # created_at + 1h
  ```
  Add to Alembic migration. CRUD in `src/crud/ai_drafts.py`.

### Architecture
- **Backend**:
  - New router `src/api/v1/ai_drafts.py` mounted in `src/api/v1/api.py`.
  - On POST: Validate AIDraftCreate, store payload (e.g., {'prompt': ..., 'generated': ai_response}), set expires_at = now + timedelta(hours=1), associate with current_user.id.
  - Signing: Extend `core/security.py` with `create_draft_token(draft_id: UUID, user_id: UUID, exp_delta: timedelta=1h) -> str` using SECRET_KEY, ALGORITHM (HS256).
  - On GET: Extract token from query, decode (verify exp, user_id matches get_current_user or allow unauth if short-lived?), fetch AIDraft by id, check !expired, return payload.
  - Validation: Strict on type/payload, delete expired drafts via cron or on fetch (soft delete?).

- **Frontend**:
  - Extend `routerConfig.tsx`: Add loaders/actions to parse `useSearchParams()` for 'ai', 'draftId', 'token', intent params (prompt, weekStart). If ai=1 && draftId, fetch via new api endpoint in `src/api/endpoints/aiDrafts.ts` using useApi hook.
  - Prefill: In RecipesNewPage/MealPlanPage, use useEffect to set store state (useRecipeStore for recipe form, useMealPlanStore for week) from fetched payload or intent params. Show AI panel if ai=1.
  - Auth: In ProtectedRoute or page-level, if !useIsAuthenticated() && ai intent, navigate(`/login?next=${encodeURIComponent(location.href)}`). On login success, redirect back via next param in useAuthStore login flow.
  - No mutations: Fetch only sets read-only initial state; user must click "Generate/Save" to mutate.

- **Security/Constraints**:
  - TTL: 1h default, configurable via env.
  - Signing: JWT with draft_id/exp/type/user_id; validate on GET against DB user_id.
  - URL Limits: Prompt <1000 chars, no PII; params JSON-serializable, size <2KB.
  - Fallback: If no draftId, use prompt/params directly for AI call; fragment (#) discouraged for privacy.

### Flows
```mermaid
sequenceDiagram
    participant U as User/UI
    participant F as Frontend
    participant B as Backend/DB
    participant A as AI Agent

    Note over U,B: Draft Creation Flow
    U->>F: POST /api/v1/ai-drafts/recipes {prompt, params}
    F->>B: Authenticated request
    B->>B: Validate, store AIDraft (payload=AI response, expires=now+1h)
    B->>B: Sign JWT {draft_id, user_id, exp, type}
    B->>F: 201 AIDraftResponse {draft_id, signed_url, expires_at}
    F->>U: Share signed_url (e.g., /recipes/new?ai=1&draftId=uuid&token=jwt)

    Note over U,B: Deep Link Load Flow (Authenticated)
    U->>F: Navigate signed_url
    F->>F: Parse params (ai=1, draftId, token)
    F->>B: GET /api/v1/ai-drafts/{draftId} ?token=jwt
    B->>B: Decode/validate token (exp, user_id)
    B->>DB: Fetch AIDraft by id, check !expired
    DB->>B: Payload
    B->>F: 200 {payload, type}
    F->>F: Prefill form/AI panel from payload
    Note over F: No mutation; wait user action

    Note over U,F: Unauthenticated Load
    U->>F: Navigate signed_url (no auth)
    F->>F: Detect ai=1 && !auth
    F->>F: Redirect /login?next=signed_url
    U->>F: Login success
    F->>F: Redirect to next (signed_url), refetch/prefill
```

Documented patterns:
- Intent-only: ?ai=1&prompt=... (no draftId, direct prefill/AI trigger).
- Draft-backed: ?ai=1&draftId=uuid&token=jwt (fetch server payload).
- Protected: All ai=1 require eventual auth; redirect preserves full link.
- Error: Invalid token/expired -> "Link expired. Start new?" -> clear params, normal UI.
- Non-AI unaffected: Existing routes ignore ai params.

## Consequences
- **Positive**:
  - Security: Signed/TTL links prevent tampering; server-side storage avoids URL leaks; auth guards sensitive fetches.
  - UX: Seamless entry to AI flows via shareable links; prefill reduces friction; explicit actions prevent surprises.
  - Extensibility: Patterns support future intents (e.g., ai=edit-recipe); JSON payload flexible for drafts.

- **Negative/Trade-offs**:
  - Complexity: New model/endpoints require migration/tests (~1 day); frontend param handling adds ~0.5 day.
  - Overhead: Short-lived DB entries (auto-purge expired); JWT signing minor perf hit.
  - Edge cases: Handle token expiry mid-session (refresh?); URL length limits prompt truncation.

- **Implementation Effort**: Medium (backend: model/router ~20h; frontend: routing/hooks ~10h; tests/docs ~5h). Low risk to core flows.
