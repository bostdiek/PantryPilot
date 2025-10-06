from uuid import uuid4

from src.schemas import ai as schemas_ai
from src.services.ai import models


def test_draft_outcome_fields_and_defaults():
    fake_draft = {"id": str(uuid4()), "payload": {}}
    token = "tok"
    outcome = models.DraftOutcome(draft=fake_draft, token=token, success=True)

    assert outcome.draft == fake_draft
    assert outcome.token == token
    assert outcome.success is True
    assert outcome.message is None

    # ensure dataclass accepts other types and preserves values
    outcome2 = models.DraftOutcome(draft=123, token="t", success=False, message="m")
    assert outcome2.draft == 123
    assert outcome2.message == "m"


def test_sse_event_terminal_helpers():
    # terminal success
    draft_id = str(uuid4())
    ev = schemas_ai.SSEEvent.terminal_success(draft_id=draft_id, success=True)
    assert ev.status == "complete"
    assert ev.step == "complete"
    assert ev.progress == 1.0
    assert ev.draft_id == draft_id
    assert ev.success is True

    # terminal error
    err = schemas_ai.SSEEvent.terminal_error(
        step="fetch_html", detail="timeout", error_code="fetch_failed"
    )
    assert err.status == "error"
    assert err.step == "fetch_html"
    assert err.progress == 1.0
    assert err.success is False
    assert err.error_code == "fetch_failed"
