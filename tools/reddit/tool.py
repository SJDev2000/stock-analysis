"""MCP tools for Reddit sentiment data."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from claude_agent_sdk import tool

from tools.reddit.client import RedditClient
from tools.reddit.fetcher import fetch_posts, fetch_posts_with_comments

logger = logging.getLogger(__name__)

_VALID_TIME_FILTERS = {"hour", "day", "week", "month", "year", "all"}
_ASSETS_DIR = Path(__file__).parent.parent.parent / "assets" / "reddit_sentiment"

_client: Optional[RedditClient] = None


def _get_client() -> RedditClient:
    global _client
    if _client is None:
        _client = RedditClient()
    return _client


def _err(msg: str) -> Dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps({"success": False, "error": msg})}],
        "is_error": True,
    }


def _asset_path(ticker: str, time_filter: str) -> Path:
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    return _ASSETS_DIR / f"{ticker.upper()}_{time_filter}.json"


@tool(
    "fetch_reddit_posts",
    (
        "Fetch Reddit posts for a stock ticker (no comments). "
        "Phase 1 of sentiment analysis — get titles and text to filter for relevance "
        "before loading comments. Returns post fields: id, subreddit, title, "
        "selftext (truncated to 300 chars), created_ist."
    ),
    {
        "ticker": Annotated[str, "Stock ticker symbol, e.g. 'NFLX', 'AAPL'"],
        "time_filter": Annotated[str, "'hour'|'day'|'week'|'month'|'year'|'all' — default 'week'"],
        "max_posts": Annotated[int, "Max posts to fetch (1–100) — default 100"],
    },
)
async def fetch_reddit_posts(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker = str(args.get("ticker", "")).upper().strip()
    time_filter = str(args.get("time_filter", "week")).lower().strip()
    max_posts = max(1, min(100, int(args.get("max_posts", 100))))

    if not ticker:
        return _err("ticker is required")
    if time_filter not in _VALID_TIME_FILTERS:
        return _err(f"time_filter must be one of {sorted(_VALID_TIME_FILTERS)}")

    try:
        fetched_at, posts = await fetch_posts(
            ticker=ticker,
            time_filter=time_filter,
            max_posts=max_posts,
            client=_get_client(),
        )
    except Exception as e:
        logger.exception("fetch_reddit_posts failed for %s", ticker)
        return _err(str(e))

    result = {
        "success": True,
        "ticker": ticker,
        "time_filter": time_filter,
        "fetched_at": fetched_at,
        "post_count": len(posts),
        "posts": [
            {
                "id": p["id"],
                "subreddit": p["subreddit"],
                "title": p["title"],
                "selftext": p["selftext"][:300],
                "created_ist": p["created_ist"],
            }
            for p in posts
        ],
    }
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}


@tool(
    "fetch_reddit_comments",
    (
        "Fetch comments for a specific list of Reddit post IDs for a ticker. "
        "Phase 2 of sentiment analysis — call after filtering posts for relevance. "
        "Saves asset to assets/reddit_sentiment/{TICKER}_{time_filter}.json with "
        "subreddit, title, selftext, and comment bodies. Returns asset path and summary."
    ),
    {
        "ticker": Annotated[str, "Stock ticker symbol, e.g. 'NFLX', 'AAPL'"],
        "post_ids": Annotated[List[str], "List of post IDs to fetch comments for"],
        "time_filter": Annotated[str, "'hour'|'day'|'week'|'month'|'year'|'all' — default 'week'"],
    },
)
async def fetch_reddit_comments(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker = str(args.get("ticker", "")).upper().strip()
    post_ids: List[str] = [str(pid) for pid in args.get("post_ids", [])]
    time_filter = str(args.get("time_filter", "week")).lower().strip()

    if not ticker:
        return _err("ticker is required")
    if not post_ids:
        return _err("post_ids is required and must be non-empty")
    if time_filter not in _VALID_TIME_FILTERS:
        return _err(f"time_filter must be one of {sorted(_VALID_TIME_FILTERS)}")

    try:
        fetched_at, posts = await fetch_posts_with_comments(
            ticker=ticker,
            post_ids=post_ids,
            time_filter=time_filter,
            client=_get_client(),
        )
    except Exception as e:
        logger.exception("fetch_reddit_comments failed for %s", ticker)
        return _err(str(e))

    asset = {
        "ticker": ticker,
        "time_filter": time_filter,
        "fetched_at": fetched_at,
        "post_count": len(posts),
        "posts": [
            {
                "subreddit": p["subreddit"],
                "title": p["title"],
                "selftext": p["selftext"],
                "comments": p.get("comments", []),
            }
            for p in posts
        ],
    }

    asset_path = _asset_path(ticker, time_filter)
    asset_path.write_text(json.dumps(asset, ensure_ascii=False, indent=2))

    total_comments = sum(len(p.get("comments", [])) for p in posts)

    result = {
        "success": True,
        "ticker": ticker,
        "time_filter": time_filter,
        "fetched_at": fetched_at,
        "posts_with_comments": len(posts),
        "total_comments": total_comments,
        "asset_path": str(asset_path),
    }
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
