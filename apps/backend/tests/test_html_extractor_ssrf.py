import socket

import pytest
from fastapi import HTTPException

from src.services.ai.html_extractor import HTMLExtractionService


def test_validate_url_rejects_loopback(monkeypatch):
    svc = HTMLExtractionService()

    # Monkeypatch getaddrinfo to return a loopback address for any host
    def fake_getaddrinfo(host, *args, **kwargs):
        return [(2, 1, 6, "", ("127.0.0.1", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(HTTPException) as exc:
        svc._validate_url("http://example.invalid")

    assert "Cannot fetch from" in str(exc.value.detail)
