import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)


def _format_timestamp(dt: datetime) -> str:
    ts = dt.astimezone(timezone.utc)
    return ts.isoformat().replace("+00:00", "Z")


class ScannerHttpClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 5.0,
        retry_attempts: int = 3,
        retry_backoff: float = 0.5,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_backoff = retry_backoff
        self._client = httpx.AsyncClient(timeout=self.timeout, transport=transport)

    def _backoff_for_attempt(self, next_attempt: int) -> float:
        """
        Backoff for the NEXT attempt (2 -> 0.5s, 3 -> 1.5s, 4+ reuse last).
        """
        steps = [self.retry_backoff, self.retry_backoff * 3]
        idx = max(0, next_attempt - 2)
        if idx >= len(steps):
            return steps[-1]
        return steps[idx]

    async def send_scan(
        self,
        direction: str,
        token: str,
        device_id: str,
        scanned_at: datetime,
    ) -> Dict[str, Any]:
        endpoint = "/api/scan/in" if direction == "in" else "/api/scan/out"
        url = f"{self.base_url}{endpoint}"
        payload = {
            "token": token,
            "timestamp": _format_timestamp(scanned_at),
            "device_id": device_id,
        }
        headers = {"X-TURNSTILE-API-KEY": self.api_key}

        last_exception: Exception | None = None

        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = await self._client.post(url, json=payload, headers=headers)
            except httpx.RequestError as exc:
                last_exception = exc
                if attempt >= self.retry_attempts:
                    break
                sleep_for = self._backoff_for_attempt(attempt + 1)
                logger.warning(
                    "Request error on %s: %s, retrying in %.1fs (attempt %s/%s)",
                    endpoint,
                    exc,
                    sleep_for,
                    attempt + 1,
                    self.retry_attempts,
                )
                await asyncio.sleep(sleep_for)
                continue

            status = response.status_code
            if status in (401, 404, 422):
                response.raise_for_status()

            if status == 429 or status >= 500:
                if attempt < self.retry_attempts:
                    sleep_for = self._backoff_for_attempt(attempt + 1)
                    logger.warning(
                        "HTTP %s on %s, retrying in %.1fs (attempt %s/%s)",
                        status,
                        endpoint,
                        sleep_for,
                        attempt + 1,
                        self.retry_attempts,
                    )
                    await asyncio.sleep(sleep_for)
                    continue
                response.raise_for_status()

            response.raise_for_status()
            return {"status": status, "body": response.json()}

        if last_exception:
            raise last_exception
        raise RuntimeError("Failed to send scan after retries")

    async def aclose(self):
        await self._client.aclose()
