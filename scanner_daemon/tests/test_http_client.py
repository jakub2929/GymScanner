import json
from datetime import datetime, timezone

import asyncio
import httpx
import pytest

from scanner_daemon.http_client import ScannerHttpClient


pytestmark = pytest.mark.asyncio


async def test_send_scan_success():
    calls = []

    async def handler(request: httpx.Request):
        calls.append(request)
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = ScannerHttpClient(
        base_url="http://api.example.com",
        api_key="secret",
        timeout=5.0,
        transport=transport,
    )
    ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
    resp = await client.send_scan("in", "tok123456789", "in-1", ts)
    await client.aclose()

    assert resp["status"] == 200
    assert resp["body"] == {"ok": True}
    assert len(calls) == 1
    req = calls[0]
    assert req.url.path == "/api/scan/in"
    assert req.headers["X-TURNSTILE-API-KEY"] == "secret"
    body = json.loads(req.content)
    assert body["token"] == "tok123456789"
    assert body["device_id"] == "in-1"
    assert body["timestamp"].endswith("Z")


async def test_send_scan_401_no_retry():
    calls = []

    async def handler(request: httpx.Request):
        calls.append(request)
        return httpx.Response(401, json={"detail": "unauthorized"})

    client = ScannerHttpClient(
        base_url="http://api.example.com",
        api_key="bad",
        timeout=5.0,
        transport=httpx.MockTransport(handler),
    )
    ts = datetime.now(timezone.utc)
    with pytest.raises(httpx.HTTPStatusError):
        await client.send_scan("out", "token", "out-1", ts)
    await client.aclose()
    assert len(calls) == 1


async def test_send_scan_429_then_success(monkeypatch):
    calls = []
    sleeps = []

    async def handler(request: httpx.Request):
        calls.append(request)
        status = 429 if len(calls) == 1 else 200
        return httpx.Response(status, json={"status": status})

    async def fake_sleep(duration: float):
        sleeps.append(duration)

    monkeypatch.setattr("scanner_daemon.http_client.asyncio.sleep", fake_sleep)

    client = ScannerHttpClient(
        base_url="http://api.example.com",
        api_key="secret",
        timeout=5.0,
        transport=httpx.MockTransport(handler),
    )
    ts = datetime.now(timezone.utc)
    resp = await client.send_scan("in", "token", "in-1", ts)
    await client.aclose()

    assert resp["status"] == 200
    assert len(calls) == 2
    assert sleeps == [0.5]


async def test_send_scan_404_no_retry():
    calls = []

    async def handler(request: httpx.Request):
        calls.append(request)
        return httpx.Response(404, json={"detail": "not found"})

    client = ScannerHttpClient(
        base_url="http://api.example.com",
        api_key="secret",
        timeout=5.0,
        transport=httpx.MockTransport(handler),
    )
    ts = datetime.now(timezone.utc)
    with pytest.raises(httpx.HTTPStatusError):
        await client.send_scan("out", "token", "out-1", ts)
    await client.aclose()
    assert len(calls) == 1
