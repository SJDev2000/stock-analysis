"""
Reddit RSS client — TTL-cached, async.

Uses Reddit's public Atom/RSS feeds which work without authentication from any IP.

User-Agent follows Reddit's required format:
    python:<app-id>:<version> (by u/<reddit_username>)

Set REDDIT_USERNAME in .env to identify your script to Reddit.

Cookie note: Reddit sets session_tracker cookies on RSS responses. Sending them
back on subsequent requests triggers 403s. We clear the cookie jar after every
successful response to keep requests stateless.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://www.reddit.com"
_BACKOFF_BASE = 5.0
_BACKOFF_MAX = 120.0
_MAX_RETRIES = 4


def _user_agent() -> str:
    username = os.environ.get("REDDIT_USERNAME", "stock_analysis_user")
    return f"python:stock.sentiment.bot:v1.0.0 (by u/{username})"


class _Cache:
    def __init__(self) -> None:
        self._store: Dict[str, Tuple[float, str]] = {}

    def get(self, key: str, ttl: float) -> Optional[str]:
        entry = self._store.get(key)
        if entry and (time.monotonic() - entry[0]) < ttl:
            return entry[1]
        return None

    def set(self, key: str, value: str) -> None:
        self._store[key] = (time.monotonic(), value)

    def clear(self) -> None:
        self._store.clear()


class RedditClient:
    """
    Async Reddit RSS client.

    Uses a single persistent httpx session. Cookie jar is cleared after each
    response — Reddit's session_tracker cookies cause 403s if resent.

    Usage:
        async with RedditClient() as client:
            xml = await client.get("/search.rss", {"q": "NFLX", "t": "week"})
    """

    def __init__(self, cache_ttl: float = 300.0) -> None:
        self._ua = _user_agent()
        self._cache = _Cache()
        self._default_ttl = cache_ttl
        self._http: Optional[httpx.AsyncClient] = None

    def _make_http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={"User-Agent": self._ua},
            timeout=15.0,
            follow_redirects=True,
            http2=False,
            # No explicit Accept header — Reddit returns 403 if Accept is set
        )

    async def __aenter__(self) -> "RedditClient":
        self._http = self._make_http()
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = self._make_http()
        return self._http

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        cache_ttl: Optional[float] = None,
    ) -> str:
        """Fetch a Reddit RSS path and return raw XML string."""
        url = _BASE + path
        if params:
            url += "?" + urlencode({k: v for k, v in params.items() if v is not None})

        ttl = cache_ttl if cache_ttl is not None else self._default_ttl
        cached = self._cache.get(url, ttl)
        if cached is not None:
            logger.debug("cache hit: %s", url)
            return cached

        xml = await self._fetch(url)
        self._cache.set(url, xml)
        return xml

    def clear_cache(self) -> None:
        self._cache.clear()

    async def _fetch(self, url: str) -> str:
        for attempt in range(_MAX_RETRIES):
            http = await self._client()
            try:
                resp = await http.get(url)
                # Clear cookie jar — Reddit's session_tracker cookies cause 403
                # on subsequent requests if sent back.
                http.cookies.clear()

                if resp.status_code == 429:
                    wait = min(
                        float(resp.headers.get("Retry-After", _BACKOFF_BASE * 2 ** attempt)),
                        _BACKOFF_MAX,
                    )
                    logger.warning("rate limited; backing off %.1f s", wait)
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code in (502, 503):
                    wait = min(_BACKOFF_BASE * 2 ** attempt, _BACKOFF_MAX)
                    logger.warning("server error %d; retry in %.1f s", resp.status_code, wait)
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code == 404:
                    raise RedditError(f"404 not found: {url}")

                resp.raise_for_status()
                return resp.text

            except (RedditError,):
                raise
            except httpx.TimeoutException:
                wait = min(_BACKOFF_BASE * 2 ** attempt, _BACKOFF_MAX)
                logger.warning("timeout; retry in %.1f s", wait)
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
            except Exception as exc:
                if attempt == _MAX_RETRIES - 1:
                    raise RedditError(str(exc)) from exc
                wait = min(_BACKOFF_BASE * 2 ** attempt, _BACKOFF_MAX)
                await asyncio.sleep(wait)

        raise RedditError(f"max retries exceeded: {url}")


class RedditError(Exception):
    pass
