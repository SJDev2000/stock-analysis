"""
Reddit RSS fetcher — returns plain dicts, no custom models.

Flow:
  1. GET /search.rss for ticker → list of post dicts
  2. GET /r/{sub}/comments/{id}.rss for each kept post → list of comment dicts
  3. Return slim asset dict ready for JSON serialisation
"""

from __future__ import annotations

import asyncio
import html
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from tools.reddit.client import RedditClient, RedditError

logger = logging.getLogger(__name__)

_A = "http://www.w3.org/2005/Atom"
_IST = timezone(timedelta(hours=5, minutes=30))
_COMMENT_CACHE_TTL = 120.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tag(local: str) -> str:
    return f"{{{_A}}}{local}"


def _text(el: ET.Element, local: str) -> str:
    child = el.find(_tag(local))
    return (child.text or "").strip() if child is not None else ""


def _parse_dt(iso: str) -> datetime:
    iso = iso.rstrip("Z")
    if iso.endswith("+00:00"):
        iso = iso[:-6]
    try:
        return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(tz=timezone.utc)


def _to_ist(dt: datetime) -> str:
    return dt.astimezone(_IST).strftime("%-d %B %Y %-I:%M %p IST")


def _now_ist() -> str:
    return datetime.now(tz=_IST).strftime("%-d %B %Y %-I:%M %p IST")


def _strip_html(raw: str) -> str:
    text = html.unescape(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"submitted by\s*/u/\S+.*$", "", text, flags=re.DOTALL).strip()
    return text


def _parse_id(full_id: str) -> str:
    return full_id.split("_", 1)[-1] if "_" in full_id else full_id


# ---------------------------------------------------------------------------
# RSS parsers — return plain dicts
# ---------------------------------------------------------------------------

def _parse_search_rss(xml: str) -> List[Dict[str, Any]]:
    posts: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        logger.warning("search RSS parse error: %s", e)
        return posts

    for entry in root.findall(_tag("entry")):
        full_id = _text(entry, "id")
        if not full_id.startswith("t3_"):
            continue

        cat = entry.find(_tag("category"))
        subreddit = (cat.get("term") or "").lower() if cat is not None else ""

        link_el = entry.find(_tag("link"))
        url = link_el.get("href", "") if link_el is not None else ""

        dt = _parse_dt(_text(entry, "published") or _text(entry, "updated"))

        posts.append({
            "id": _parse_id(full_id),
            "subreddit": subreddit,
            "title": _text(entry, "title"),
            "selftext": _strip_html(_text(entry, "content")),
            "url": url,
            "created_ist": _to_ist(dt),
        })

    return posts


def _parse_comments_rss(xml: str) -> List[Dict[str, Any]]:
    comments: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        logger.warning("comments RSS parse error: %s", e)
        return comments

    for entry in root.findall(_tag("entry")):
        full_id = _text(entry, "id")
        if not full_id.startswith("t1_"):
            continue

        body = _strip_html(_text(entry, "content"))
        if not body or body in ("[deleted]", "[removed]"):
            continue

        dt = _parse_dt(_text(entry, "updated"))
        comments.append({
            "body": body,
            "created_ist": _to_ist(dt),
        })

    return comments


# ---------------------------------------------------------------------------
# Fetch orchestration
# ---------------------------------------------------------------------------

async def _fetch_comments(
    client: RedditClient,
    subreddit: str,
    post_id: str,
) -> List[Dict[str, Any]]:
    try:
        xml = await client.get(
            f"/r/{subreddit}/comments/{post_id}.rss",
            cache_ttl=_COMMENT_CACHE_TTL,
        )
    except RedditError as e:
        logger.warning("comment fetch failed %s/%s: %s", subreddit, post_id, e)
        return []
    return _parse_comments_rss(xml)


async def fetch_posts(
    ticker: str,
    time_filter: str = "week",
    max_posts: int = 100,
    client: Optional[RedditClient] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (fetched_at_ist, list_of_post_dicts) — no comments."""
    async def _run(c: RedditClient) -> Tuple[str, List[Dict[str, Any]]]:
        xml = await c.get("/search.rss", {"q": ticker, "t": time_filter, "type": "posts", "limit": 100})
        posts = _parse_search_rss(xml)[:max_posts]
        return _now_ist(), posts

    if client is not None:
        return await _run(client)
    async with RedditClient() as c:
        return await _run(c)


async def fetch_posts_with_comments(
    ticker: str,
    post_ids: List[str],
    time_filter: str = "week",
    client: Optional[RedditClient] = None,
    concurrency: int = 10,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Fetch posts (filtered to post_ids) plus their comments.
    Returns (fetched_at_ist, list_of_post_dicts_with_comments_key).
    """
    async def _run(c: RedditClient) -> Tuple[str, List[Dict[str, Any]]]:
        xml = await c.get("/search.rss", {"q": ticker, "t": time_filter, "type": "posts", "limit": 100})
        all_posts = _parse_search_rss(xml)
        kept = [p for p in all_posts if p["id"] in set(post_ids)]

        sem = asyncio.Semaphore(concurrency)

        async def _add_comments(post: Dict[str, Any]) -> None:
            async with sem:
                post["comments"] = await _fetch_comments(c, post["subreddit"], post["id"])

        await asyncio.gather(*(_add_comments(p) for p in kept))
        return _now_ist(), kept

    if client is not None:
        return await _run(client)
    async with RedditClient() as c:
        return await _run(c)
