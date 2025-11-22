import logging

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.routes import scanner


def make_request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": ("testclient", 123),
    }
    return Request(scope)


def test_require_api_key_accepts(monkeypatch):
    monkeypatch.setenv("TURNSTILE_API_KEY", "secret")
    req = make_request({"X-TURNSTILE-API-KEY": "secret"})
    scanner._require_api_key(req)  # should not raise


def test_require_api_key_rejects(monkeypatch):
    monkeypatch.setenv("TURNSTILE_API_KEY", "secret")
    req = make_request({"X-TURNSTILE-API-KEY": "wrong"})
    with pytest.raises(HTTPException):
        scanner._require_api_key(req)


def test_rate_limit_blocks_close_calls(monkeypatch):
    scanner._last_request_per_scanner.clear()
    times = iter([0.0, 0.01])
    monkeypatch.setattr(scanner.time, "monotonic", lambda: next(times))
    scanner._enforce_rate_limit("in-1")
    with pytest.raises(HTTPException):
        scanner._enforce_rate_limit("in-1")


def test_rate_limit_allows_after_window(monkeypatch):
    scanner._last_request_per_scanner.clear()
    times = iter([0.0, 0.1])
    monkeypatch.setattr(scanner.time, "monotonic", lambda: next(times))
    scanner._enforce_rate_limit("in-1")
    scanner._enforce_rate_limit("in-1")  # no exception after 100 ms


def test_log_422_throttled(monkeypatch, caplog):
    scanner._last_422_log_per_scanner.clear()
    times = iter([0.0, 0.2, 0.9, 1.5])
    monkeypatch.setattr(scanner.time, "monotonic", lambda: next(times))

    caplog.set_level(logging.WARNING)
    scanner._log_422_throttled("in-1", "first")
    scanner._log_422_throttled("in-1", "second")
    scanner._log_422_throttled("in-1", "third")
    scanner._log_422_throttled("in-1", "fourth")

    messages = [rec.message for rec in caplog.records if rec.levelno == logging.WARNING]
    assert messages == ["first", "fourth"]
