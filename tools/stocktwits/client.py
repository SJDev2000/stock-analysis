"""
Stocktwits public API client — async, with exponential backoff on rate limits.

Endpoint: GET https://api.stocktwits.com/api/2/streams/symbol/{TICKER}.json
Returns the 30 most recent messages for a ticker. No auth required.

Rate limits: 200 requests/hour per IP. Responds 429 on breach.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.stocktwits.com/api/2"
_BACKOFF_BASE = 2.0
_BACKOFF_MAX = 60.0
_MAX_RETRIES = 5


class StocktwitsClient:
    def __init__(self) -> None:
        self._http: httpx.AsyncClient | None = None

    def _make_http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={"User-Agent": "stock-analysis-agent/1.0"},
            timeout=15.0,
            follow_redirects=True,
        )

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = self._make_http()
        return self._http

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    async def get_symbol_stream(self, ticker: str) -> Dict[str, Any]:
        """Fetch latest 30 messages for ticker. Returns parsed JSON dict."""
        url = f"{_BASE}/streams/symbol/{ticker.upper()}.json"
        return await self._fetch_json(url)

    async def _fetch_json(self, url: str) -> Dict[str, Any]:
        for attempt in range(_MAX_RETRIES):
            http = await self._client()
            try:
                resp = await http.get(url)

                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("X-RateLimit-Reset", _BACKOFF_BASE * (2 ** attempt)))
                    wait = min(retry_after, _BACKOFF_MAX)
                    logger.warning("Stocktwits rate limited; backing off %.1f s (attempt %d)", wait, attempt + 1)
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code in (502, 503, 504):
                    wait = min(_BACKOFF_BASE * (2 ** attempt), _BACKOFF_MAX)
                    logger.warning("Stocktwits server error %d; retry in %.1f s", resp.status_code, wait)
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code == 404:
                    raise StocktwitsError(f"Symbol not found: {url}")

                resp.raise_for_status()
                return resp.json()

            except StocktwitsError:
                raise
            except httpx.TimeoutException:
                wait = min(_BACKOFF_BASE * (2 ** attempt), _BACKOFF_MAX)
                logger.warning("Stocktwits timeout; retry in %.1f s", wait)
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
            except Exception as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise StocktwitsError(str(exc)) from exc
                wait = min(_BACKOFF_BASE * (2 ** attempt), _BACKOFF_MAX)
                await asyncio.sleep(wait)

        raise StocktwitsError(f"Max retries exceeded for {url}")


class StocktwitsError(Exception):
    pass
