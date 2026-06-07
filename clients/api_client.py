from __future__ import annotations

import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional, Union

import httpx

logger = logging.getLogger(__name__)

_BACKOFF_BASE = 2.0
_BACKOFF_MAX = 120.0
_MAX_RETRIES = 5

ResponseType = Union[ET.Element, str]


class ApiError(Exception):
    pass


class ApiClient:
    """
    Generic async HTTP client with exponential backoff and retry.

    - XML responses are parsed and returned as ET.Element.
    - JSON / other responses are returned as resp.text.

    Usage:
        async with ApiClient(base_url, headers=...) as client:
            tree = await client.get("/search.rss", params={...}, accept="xml")
            text = await client.get("/api/stream.json", accept="json")
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._timeout = timeout
        self._http: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "ApiClient":
        self._http = self._make_http()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    def _make_http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=self._timeout,
            follow_redirects=True,
            verify=False,
        )

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = self._make_http()
        return self._http

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        accept: str = "json",
        clear_cookies: bool = False,
    ) -> ResponseType:
        """
        GET `path` and return parsed content.

        Args:
            path: URL path relative to base_url.
            params: Query parameters (None values are dropped).
            accept: "xml" → returns ET.Element; anything else → returns resp.text.
            clear_cookies: If True, clears the cookie jar after each response
                           (needed for Reddit RSS to avoid 403s).
        """
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}

        for attempt in range(_MAX_RETRIES):
            http = await self._client()
            try:
                resp = await http.get(path, params=clean_params)

                if clear_cookies:
                    http.cookies.clear()

                if resp.status_code == 429:
                    wait = min(
                        float(resp.headers.get("Retry-After", _BACKOFF_BASE * 2 ** attempt)),
                        _BACKOFF_MAX,
                    )
                    logger.warning("rate limited; backing off %.1f s", wait)
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code in (502, 503, 504):
                    wait = min(_BACKOFF_BASE * 2 ** attempt, _BACKOFF_MAX)
                    logger.warning("server error %d; retry in %.1f s", resp.status_code, wait)
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code == 404:
                    raise ApiError(f"404 not found: {self._base_url}{path}")

                resp.raise_for_status()

                if accept == "xml":
                    try:
                        return ET.fromstring(resp.text)
                    except ET.ParseError as exc:
                        raise ApiError(f"XML parse error: {exc}") from exc

                return resp.text

            except ApiError:
                raise
            except httpx.TimeoutException:
                wait = min(_BACKOFF_BASE * 2 ** attempt, _BACKOFF_MAX)
                logger.warning("timeout; retry in %.1f s", wait)
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
            except Exception as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise ApiError(str(exc)) from exc
                wait = min(_BACKOFF_BASE * 2 ** attempt, _BACKOFF_MAX)
                await asyncio.sleep(wait)

        raise ApiError(f"max retries exceeded: {self._base_url}{path}")
