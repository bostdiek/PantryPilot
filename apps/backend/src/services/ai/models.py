"""Domain models for AI extraction orchestration (Phase 2 additions).

This module introduces two explicit, typed contract objects used by the
`Orchestrator` implementation and API layer:

* DraftOutcome  - Result of a non‑streaming extraction attempt (authoritative
  return type; no tuple fallback maintained).
* SSEEvent      - Structured Server Sent Event payload used by the streaming
  extraction flow. The orchestrator now emits structured events which are
  serialized to the SSE wire format in a single place to keep schema uniform.

Having these models makes downstream reasoning, testing, and refactoring easier
and prevents ad hoc dict construction from drifting over time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar


DraftT = TypeVar("DraftT")


@dataclass(slots=True)
class DraftOutcome(Generic[DraftT]):  # noqa: UP046 (retain legacy syntax for parser compatibility)
    """Structured result of a draft extraction attempt (no legacy tuple form)."""

    draft: DraftT
    token: str
    success: bool
    message: str | None = None


# Note: SSEEvent moved to `schemas.ai` for API contract visibility.
