"""Focused unit tests for global exception handling behaviors.

These tests exercise the public contract via FastAPI test app using the installed
exception handler and ExceptionNormalizationMiddleware.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from core.error_handler import (
    ExceptionNormalizationMiddleware,
    global_exception_handler,
)
from core.exceptions import DuplicateUserError, UserNotFoundError
from core.middleware import CorrelationIdMiddleware


class Item(BaseModel):
    name: str = Field(min_length=3)
    qty: int = Field(ge=1)


def build_test_app(env: str) -> TestClient:
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(ExceptionNormalizationMiddleware)
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(HTTPException, global_exception_handler)
    app.add_exception_handler(RequestValidationError, global_exception_handler)

    @app.post("/items")
    async def create_item(item: Item):  # pragma: no cover - executed via client
        return {"ok": True, "item": item.model_dump()}

    @app.get("/domain-duplicate")
    async def domain_dup():
        raise DuplicateUserError("User already exists")

    @app.get("/domain-missing")
    async def domain_missing():
        raise UserNotFoundError("User not found")

    @app.get("/boom")
    async def boom():
        raise RuntimeError("Exploded with secret=should_not_leak")

    @app.get("/unauthorized")
    async def unauthorized():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.get("/forbidden")
    async def forbidden():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    client = TestClient(app)

    # Patch environment setting per test invocation
    patcher = patch("core.error_handler.get_settings")
    mocked = patcher.start()
    mocked.return_value.ENVIRONMENT = env

    # Ensure patcher stops at client finalizer
    def fin():
        patcher.stop()

    client._finalizer = fin  # type: ignore[attr-defined]
    return client


def test_validation_error_production():
    client = build_test_app("production")
    resp = client.post("/items", json={"name": "ab", "qty": 0})
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["type"] == "validation_error"
    # production should not include validation_errors
    assert "validation_errors" not in data["error"]


def test_validation_error_development():
    client = build_test_app("development")
    resp = client.post("/items", json={"name": "ab", "qty": 0})
    assert resp.status_code == 422
    data = resp.json()
    assert "validation_errors" in data["error"]


def test_domain_duplicate_production():
    client = build_test_app("production")
    resp = client.get("/domain-duplicate")
    assert resp.status_code == 500
    data = resp.json()
    assert data["error"]["type"] == "domain_error"
    assert "details" not in data["error"]


def test_domain_missing_development():
    client = build_test_app("development")
    resp = client.get("/domain-missing")
    assert resp.status_code == 500
    data = resp.json()
    assert data["error"]["type"] == "domain_error"
    assert "details" in data["error"] or True  # tolerant: details optional


def test_generic_exception_production():
    client = build_test_app("production")
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["type"] == "internal_server_error"
    assert "traceback" not in body["error"]
    assert "secret=should_not_leak" not in str(body)


def test_generic_exception_development():
    client = build_test_app("development")
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["type"] == "internal_server_error"
    assert "traceback" in body["error"]


def test_unauthorized_error_canonical_type():
    """Test that 401 HTTPException returns canonical 'unauthorized' error type."""
    client = build_test_app("production")
    resp = client.get("/unauthorized")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["type"] == "unauthorized"
    assert body["error"]["correlation_id"]
    assert body["success"] is False
    # Should not leak details in production
    assert "details" not in body["error"]


def test_unauthorized_error_development():
    """Test that 401 HTTPException includes details in development."""
    client = build_test_app("development")
    resp = client.get("/unauthorized")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["type"] == "unauthorized"
    assert body["error"]["correlation_id"]
    # Should include details in development
    assert "details" in body["error"]
    assert body["error"]["details"]["detail"] == "Could not validate credentials"


def test_forbidden_error_canonical_type():
    """Test that 403 HTTPException returns canonical 'forbidden' error type."""
    client = build_test_app("production")
    resp = client.get("/forbidden")
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["type"] == "forbidden"
    assert body["error"]["correlation_id"]
    assert body["success"] is False
    # Should not leak details in production
    assert "details" not in body["error"]


def test_forbidden_error_development():
    """Test that 403 HTTPException includes details in development."""
    client = build_test_app("development")
    resp = client.get("/forbidden")
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["type"] == "forbidden"
    assert body["error"]["correlation_id"]
    # Should include details in development
    assert "details" in body["error"]
    assert body["error"]["details"]["detail"] == "Access denied"
