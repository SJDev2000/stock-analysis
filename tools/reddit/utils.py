"""RedditUtils — stateless helpers for RSS parsing and MCP response building."""

from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from clients.api_client import ApiClient
from tools.reddit.models import RedditComment, RedditPost
from common_utilities import parse_dt, strip_html, to_ist

_ASSETS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "reddit"
_BASE_URL    = "https://www.reddit.com"
_ATOM_NS     = "http://www.w3.org/2005/Atom"


class RedditUtils:
    """Stateless helpers — call as class methods."""

    # ------------------------------------------------------------------ #
    # HTTP client factory                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def make_client() -> ApiClient:
        username = os.environ.get("REDDIT_USERNAME", "stock_analysis_user")
        return ApiClient(
            base_url=_BASE_URL,
            headers={"User-Agent": f"python:stock.sentiment.bot:v1.0.0 (by u/{username})"},
        )

    # ------------------------------------------------------------------ #
    # Asset persistence                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def asset_path(ticker: str, time_filter: str) -> Path:
        _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        return _ASSETS_DIR / f"{ticker.upper()}_reddit_{time_filter}.json"

    @staticmethod
    def save_asset(path: Path, data: Any) -> None:
        # Clear all stale reddit files for this ticker before writing
        for stale in path.parent.glob(f"{path.name.split('_reddit_')[0]}_reddit_*.json"):
            stale.unlink(missing_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    # ------------------------------------------------------------------ #
    # MCP response builders                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def ok_response(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}]}

    @staticmethod
    def err_response(error: str, **extra) -> Dict[str, Any]:
        payload = {"success": False, "error": error, **extra}
        return {
            "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
            "is_error": True,
        }

    # ------------------------------------------------------------------ #
    # Atom/RSS XML helpers                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def tag(local: str) -> str:
        return f"{{{_ATOM_NS}}}{local}"

    @staticmethod
    def text(el: ET.Element, local: str) -> str:
        child = el.find(RedditUtils.tag(local))
        return (child.text or "").strip() if child is not None else ""

    @staticmethod
    def parse_id(full_id: str) -> str:
        return full_id.split("_", 1)[-1] if "_" in full_id else full_id

    # ------------------------------------------------------------------ #
    # RSS document parsers                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def parse_posts(root: ET.Element) -> List[RedditPost]:
        posts: List[RedditPost] = []
        for entry in root.findall(RedditUtils.tag("entry")):
            full_id = RedditUtils.text(entry, "id")
            if not full_id.startswith("t3_"):
                continue
            cat     = entry.find(RedditUtils.tag("category"))
            subreddit = (cat.get("term") or "").lower() if cat is not None else ""
            link_el = entry.find(RedditUtils.tag("link"))
            url     = link_el.get("href", "") if link_el is not None else ""
            dt      = parse_dt(RedditUtils.text(entry, "published") or RedditUtils.text(entry, "updated"))
            posts.append(RedditPost(
                id        = RedditUtils.parse_id(full_id),
                subreddit = subreddit,
                title     = RedditUtils.text(entry, "title"),
                selftext  = strip_html(RedditUtils.text(entry, "content")),
                url       = url,
                created_ist = to_ist(dt),
            ))
        return posts

    @staticmethod
    def parse_comments(root: ET.Element) -> List[RedditComment]:
        comments: List[RedditComment] = []
        for entry in root.findall(RedditUtils.tag("entry")):
            full_id = RedditUtils.text(entry, "id")
            if not full_id.startswith("t1_"):
                continue
            body = strip_html(RedditUtils.text(entry, "content"))
            if not body or body in ("[deleted]", "[removed]"):
                continue
            dt = parse_dt(RedditUtils.text(entry, "updated"))
            comments.append(RedditComment(body=body, created_ist=to_ist(dt)))
        return comments
