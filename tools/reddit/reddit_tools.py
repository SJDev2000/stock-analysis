"""MCP tools for Reddit sentiment data."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Annotated, Any, Dict, List

from claude_agent_sdk import tool

from tools.reddit.fetcher import RedditFetcher
from tools.reddit.utils import RedditUtils

logger  = logging.getLogger(__name__)
_fetcher = RedditFetcher()

_VALID_TIME_FILTERS = {"hour", "day", "week", "month", "year", "all"}


@tool(
    "fetch_reddit_posts",
    "Fetch Reddit posts for a stock ticker (no comments). "
    "Phase 1 of sentiment analysis — get titles and text to filter for relevance "
    "before loading comments. Returns post fields: id, subreddit, title, "
    "selftext (truncated to 300 chars), created_ist.",
    {
        "ticker":      Annotated[str, "Stock ticker symbol, e.g. 'NFLX', 'AAPL'"],
        "time_filter": Annotated[str, "'hour'|'day'|'week'|'month'|'year'|'all' — default 'week'"],
        "max_posts":   Annotated[int, "Max posts to fetch (1–100) — default 100"],
    },
)
async def fetch_reddit_posts(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker      = str(args.get("ticker", "")).upper().strip()
    time_filter = str(args.get("time_filter", "week")).lower().strip()
    max_posts   = max(1, min(100, int(args.get("max_posts", 100))))

    if not ticker:
        return RedditUtils.err_response("ticker is required")
    if time_filter not in _VALID_TIME_FILTERS:
        return RedditUtils.err_response(f"time_filter must be one of {sorted(_VALID_TIME_FILTERS)}")

    try:
        fetched_at, posts = await _fetcher.fetch_posts(ticker, time_filter, max_posts)
    except Exception as e:
        logger.exception("fetch_reddit_posts failed for %s", ticker)
        return RedditUtils.err_response(str(e), ticker=ticker)

    return RedditUtils.ok_response({
        "success":      True,
        "ticker":       ticker,
        "time_filter":  time_filter,
        "fetched_at":   fetched_at,
        "post_count":   len(posts),
        "posts": [
            {
                "id":          p.id,
                "subreddit":   p.subreddit,
                "title":       p.title,
                "selftext":    p.selftext[:300],
                "created_ist": p.created_ist,
            }
            for p in posts
        ],
    })


@tool(
    "fetch_reddit_comments",
    "Fetch comments for a specific list of Reddit post IDs for a ticker. "
    "Phase 2 of sentiment analysis — call after filtering posts for relevance. "
    "Saves artifact to artifacts/reddit/{TICKER}_{time_filter}.json with "
    "subreddit, title, selftext, and comment bodies. Returns asset path and summary.",
    {
        "ticker":      Annotated[str, "Stock ticker symbol, e.g. 'NFLX', 'AAPL'"],
        "post_ids":    Annotated[str, "Comma-separated list of post IDs, e.g. 'abc123,def456'"],
        "time_filter": Annotated[str, "'hour'|'day'|'week'|'month'|'year'|'all' — default 'week'"],
    },
)
async def fetch_reddit_comments(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker      = str(args.get("ticker", "")).upper().strip()
    raw_ids     = args.get("post_ids", "")
    post_ids: List[str] = (
        [str(pid).strip() for pid in raw_ids if str(pid).strip()]
        if isinstance(raw_ids, list)
        else [pid.strip() for pid in str(raw_ids).split(",") if pid.strip()]
    )
    time_filter = str(args.get("time_filter", "week")).lower().strip()

    if not ticker:
        return RedditUtils.err_response("ticker is required")
    if not post_ids:
        return RedditUtils.err_response("post_ids is required and must be non-empty")
    if time_filter not in _VALID_TIME_FILTERS:
        return RedditUtils.err_response(f"time_filter must be one of {sorted(_VALID_TIME_FILTERS)}")

    try:
        fetched_at, posts = await _fetcher.fetch_posts_with_comments(ticker, post_ids, time_filter)
    except Exception as e:
        logger.exception("fetch_reddit_comments failed for %s", ticker)
        return RedditUtils.err_response(str(e), ticker=ticker)

    asset = {
        "ticker":      ticker,
        "time_filter": time_filter,
        "fetched_at":  fetched_at,
        "post_count":  len(posts),
        "posts": [
            {
                "subreddit": p.subreddit,
                "title":     p.title,
                "selftext":  p.selftext,
                "comments":  [asdict(c) for c in p.comments],
            }
            for p in posts
        ],
    }
    path = RedditUtils.asset_path(ticker, time_filter)
    RedditUtils.save_asset(path, asset)

    total_comments = sum(len(p.comments) for p in posts)
    return RedditUtils.ok_response({
        "success":             True,
        "ticker":              ticker,
        "report_type":         "reddit_comments",
        "time_filter":         time_filter,
        "fetched_at":          fetched_at,
        "posts_with_comments": len(posts),
        "total_comments":      total_comments,
        "asset_path":          str(path),
    })
