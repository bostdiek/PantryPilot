import json

from src.core.error_handler import _build_error_response


def test_build_error_response_production_hides_optional_fields():
    resp = _build_error_response(
        correlation_id="cid",
        error_type="internal_server_error",
        message="An internal error occurred",
        environment="production",
        details={"debug": True},
        traceback_str="trace",
        exception_type="ValueError",
        validation_errors={"x": 1},
        status_code=500,
    )
    # The JSONResponse produced here stores the rendered bytes in `body`
    body = json.loads(resp.body)

    assert resp.status_code == 500
    # In production only correlation_id and type should be present in error
    assert body["error"]["correlation_id"] == "cid"
    assert body["error"]["type"] == "internal_server_error"
    assert "details" not in body["error"]
    assert "traceback" not in body["error"]
    assert "exception_type" not in body["error"]
    assert "validation_errors" not in body["error"]


def test_build_error_response_development_includes_optional_fields():
    resp = _build_error_response(
        correlation_id="cid",
        error_type="internal_server_error",
        message="An internal error occurred",
        environment="development",
        details={"debug": True},
        traceback_str="trace",
        exception_type="ValueError",
        validation_errors={"x": 1},
        status_code=500,
    )
    # Read rendered body bytes directly (Starlette/fastapi versions differ)
    body = json.loads(resp.body)

    assert resp.status_code == 500
    # Development environment exposes additional fields
    assert body["error"]["details"] == {"debug": True}
    assert "traceback" in body["error"]
    assert body["error"]["exception_type"] == "ValueError"
    assert body["error"]["validation_errors"] == {"x": 1}
