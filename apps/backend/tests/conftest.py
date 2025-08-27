"""
Shared test fixtures for pytest.
"""

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from dependencies.db import get_db
from main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Create a test client for the FastAPI application.
    """
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async test client for the FastAPI application.
    """

    # Minimal fake async SQLAlchemy session for tests
    class _FakeResult:
        def scalars(self):
            return self

        def first(self):
            return None

    class _FakeSession:
        def add(self, _obj):
            # No-op add; objects already have IDs assigned in code
            return None

        async def flush(self):
            return None

        async def execute(self, _stmt):
            # Return empty result so ingredients get created
            return _FakeResult()

        async def commit(self):
            return None

        async def rollback(self):
            return None

        async def close(self):
            return None

    async def _override_get_db():
        fake = _FakeSession()
        try:
            yield fake
        finally:
            await fake.close()

    # Apply dependency override
    app.dependency_overrides[get_db] = _override_get_db
    # Create a transport that uses the FastAPI app
    transport = ASGITransport(app=app)

    # Create an AsyncClient with the transport and a proper base URL with scheme
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        try:
            yield client
        finally:
            # Clean override to avoid bleeding between tests
            app.dependency_overrides.pop(get_db, None)
