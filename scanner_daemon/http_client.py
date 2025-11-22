import asyncio
import logging
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)


class ScannerHttpClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 5.0,
        retry_attempts: int = 3,
        retry_backoff: float = 1.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_backoff = retry_backoff
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def send_scan(
        self, direction: str, token: str, scanner_id: str, raw_data: str | None
    ) -> Dict[str, Any]:
        endpoint = "/api/scanner/in" if direction == "in" else "/api/scanner/out"
        url = f"{self.base_url}{endpoint}"
        payload = {
            "token": token,
            "scanner_id": scanner_id,
            "raw_data": raw_data,
        }
        headers = {"X-TURNSTILE-API-KEY": self.api_key}

        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = await self._client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                # Retry on server errors; return on client errors
                if exc.response.status_code >= 500 and attempt < self.retry_attempts:
                    sleep_for = self.retry_backoff * attempt
                    logger.warning(
                        "HTTP %s on %s, retrying in %.1fs (attempt %s/%s)",
                        exc.response.status_code,
                        endpoint,
                        sleep_for,
                        attempt,
                        self.retry_attempts,
                    )
                    await asyncio.sleep(sleep_for)
                    continue
                raise
            except httpx.RequestError as exc:
                if attempt >= self.retry_attempts:
                    raise
                sleep_for = self.retry_backoff * attempt
                logger.warning(
                    "Request error on %s: %s, retrying in %.1fs (attempt %s/%s)",
                    endpoint,
                    exc,
                    sleep_for,
                    attempt,
                    self.retry_attempts,
                )
                await asyncio.sleep(sleep_for)

    async def aclose(self):
        await self._client.aclose()
