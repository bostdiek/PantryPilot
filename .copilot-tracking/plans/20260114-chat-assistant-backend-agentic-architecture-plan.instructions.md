---
applyTo: ".copilot-tracking/changes/20260114-chat-assistant-backend-agentic-architecture-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Nibble Chat Assistant Backend Agentic Architecture

## Overview

Plan and implement the Nibble chat assistant backend architecture (Story 2) with SSE streaming, multimodal message blocks, explicit tool confirmation, durable persistence, and user-editable memory, aligned to existing PantryPilot backend patterns.

Follow all instructions from #file:../../.github/instructions/task-implementation.instructions.md

## Objectives

- Standardize an SSE streaming endpoint and event envelope contract for assistant responses.
- Define multimodal content blocks for both streaming and persistence.
- Define a safe tool-calling pattern where DB-mutating actions require (propose → accept/cancel → execute), and read-only tools auto-execute with audit history and cancel retention.
- Define persistence schemas for conversations, messages, tool calls, and pending actions, including summaries and retention rules.
- Define MVP durable memory as a single user-editable memory document with an automatic “as necessary” update policy.
- Specify weather + web search tool constraints (daily-only forecast; 3-URL ingestion cap) and observability guidance for Azure.

## Research Summary

### Project Files

- apps/backend/src/api/v1/ai.py - existing SSE streaming and token-gated public fetch patterns.
- apps/backend/src/schemas/ai.py - existing `SSEEvent` precedent with `.to_sse()`.
- apps/backend/src/core/ratelimit.py - Upstash-backed `check_rate_limit` dependency.
- apps/backend/src/dependencies/auth.py - router-level auth dependency (`get_current_user`) and access helpers.
- apps/backend/src/core/security.py - JWT token helpers used for signed deep links.
- apps/backend/src/api/v1/api.py - router registration and dependency patterns.

### External References

- .copilot-tracking/research/20260114-chat-assistant-backend-agentic-architecture-research.md - authoritative Story 2 backend architecture decisions (streaming, tools, persistence, memory, observability).
- https://ai.pydantic.dev/ui/overview/ - event streaming guidance for UI backends.
- https://ai.pydantic.dev/output/ - `run_stream_events()` guidance for full event streaming.
- https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable?tabs=python - Azure Monitor OpenTelemetry distro for Python.
- https://open-meteo.com/en/docs - daily forecast API variables.
- https://api.search.brave.com/app/documentation/web-search/get-started - Brave Web Search API for programmatic results.

### Standards References

- #file:../../.github/instructions/backend-python-fastapi.instructions.md - FastAPI backend conventions (DI, routers, schemas).
- #file:../../.github/instructions/uv-projects.instructions.md - Python environment/tooling conventions.
- #file:../../.github/instructions/task-implementation.instructions.md - required change tracking workflow.

## Implementation Checklist

### [x] Phase 1: Streaming + Content Contracts

- [x] Task 1.1: Define SSE transport + event envelope

  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 12-32)

- [x] Task 1.2: Define multimodal content blocks (canonical message model)

  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 33-51)

- [x] Task 1.3: Implement PydanticAI `Agent.to_web()` dev runner (playground)
  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 52-75)

### [ ] Phase 2: Conversation Persistence + Summaries + Retention

- [ ] Task 2.1: Define core persistence schema (conversations + messages)

  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 78-93)

- [ ] Task 2.2: Define retention policy + enforcement mechanism

  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 94-109)

- [ ] Task 2.3: Define summary update policy + events
  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 110-125)

### [ ] Phase 3: Tool Calling (“Propose → Accept → Execute”) + Auditing

- [ ] Task 3.1: Define tool proposal + accept/cancel flow contracts

  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 128-151)

- [ ] Task 3.2: Define normalized tool call history (auditable records)
  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 152-167)

### [ ] Phase 4: Durable User Memory + Profile Location

- [ ] Task 4.1: Define “memory document” storage + user edit endpoints

  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 170-187)

- [ ] Task 4.2: Define user profile location fields + geocoding policy
  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 188-203)

### [ ] Phase 5: External Tools (Weather + Web Search)

- [ ] Task 5.1: Weather tool interface + provider choice

  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 206-220)

- [ ] Task 5.2: Web search tool provider + ingestion cap
  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 221-238)

### [ ] Phase 6: Security Alignment + Observability + Dev UX

- [ ] Task 6.1: Align auth + rate limiting with existing backend patterns

  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 241-258)

- [ ] Task 6.2: Define observability stack and safe logging constraints

  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 259-275)

- [ ] Task 6.3: Define developer workflow for prompt/tool iteration
  - Details: .copilot-tracking/details/20260114-chat-assistant-backend-agentic-architecture-details.md (Lines 276-290)

## Dependencies

- FastAPI + async SQLAlchemy + Alembic (existing repo stack)
- PydanticAI (agent + tool primitives; local `Agent.to_web()` UI)
- Upstash-backed rate limiting dependency (`check_rate_limit`)
- External APIs (future implementation): Open-Meteo, Weather.gov, Brave Search API
- Azure Monitor / Application Insights (production observability target)

## Success Criteria

- SSE transport + event envelope + event list is finalized and implemented consistently.
- Multimodal block schema is implemented and supports incremental frontend adoption.
- Tool calling accept flow is implemented with audit history, and cancellations are retained with optional reason.
- Persistence schema is implemented via Alembic migrations and supports summaries + retention policy.
- Memory doc is implemented with “as necessary” update gating and user edit controls.
- Weather + web search tools enforce the locked constraints (daily-only forecast; 3-URL cap).
- Auth + rate limiting + observability align with existing PantryPilot backend patterns.

## PR & Branching Strategy

This plan is intentionally large; implement it via multiple small PRs.

### Branch Naming (standard slug)

Use a lowercase, hyphenated slug prefixed by `feature/` and a two-digit increment to keep ordering obvious:

- `feature/20260114-chat-assistant-backend-agentic-architecture-01-streaming-contracts`
- `feature/20260114-chat-assistant-backend-agentic-architecture-02-persistence-schema`
- `feature/20260114-chat-assistant-backend-agentic-architecture-03-tool-accept-flow`
- `feature/20260114-chat-assistant-backend-agentic-architecture-04-memory-doc-profile-location`
- `feature/20260114-chat-assistant-backend-agentic-architecture-05-external-tools-observability`

If you decide to combine phases, keep the same format and adjust the suffix.

### When to Open PRs

- PR 01 (after Phase 1): Streaming + content contracts are implemented end-to-end (SSE envelope + block schemas).
  - Demo milestone: add a minimal local agent runner (PydanticAI Web UI) with 1–2 read-only tools so you can immediately “play with the agent” and observe tool selection and event streaming.
- PR 02 (after Phase 2): Core persistence schema is implemented (models + migrations) without tool execution side effects yet.
- PR 03 (after Phase 3): Tool proposal + accept/cancel flow is implemented and audited.
- PR 04 (after Phase 4): Memory doc + profile location fields + geocoding policy are implemented.
- PR 05 (after Phase 5 and Phase 6): Weather/search tool wrappers + observability init + rate limiting alignment are implemented.

Notes:

- It’s OK if PR 02 and PR 03 swap depending on implementation dependencies, but avoid mixing persistence + external tool integrations in the same PR.
- If the goal is early iteration on agent behavior, prioritize the PR 01 demo milestone (agent runner + read-only tools) even if the production endpoints are still stubbed.
