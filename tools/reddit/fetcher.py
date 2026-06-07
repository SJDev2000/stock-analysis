"""RedditFetcher — network I/O only, no MCP wiring."""

from __future__ import annotations

import asyncio
import logging
from typing import List, Tuple

from clients.api_client import ApiError
from tools.reddit.models import RedditComment, RedditPost
from tools.reddit.utils import RedditUtils
from common_utilities import now_ist

logger = logging.getLogger(__name__)

_CONCURRENCY = 10


class RedditFetcher:
    """Fetches posts and comments from Reddit RSS feeds."""

    async def fetch_posts(
        self,
        ticker: str,
        time_filter: str = "week",
        max_posts: int = 100,
    ) -> Tuple[str, List[RedditPost]]:
        """Return (fetched_at_ist, posts) with no comments attached."""
        async with RedditUtils.make_client() as client:
            root = await client.get(
                "/search.rss",
                params={"q": ticker, "t": time_filter, "type": "posts", "limit": 100},
                accept="xml",
                clear_cookies=True,
            )
        return now_ist(), RedditUtils.parse_posts(root)[:max_posts]

    async def fetch_posts_with_comments(
        self,
        ticker: str,
        post_ids: List[str],
        time_filter: str = "week",
    ) -> Tuple[str, List[RedditPost]]:
        """Fetch posts matching post_ids then attach their comments concurrently."""
        async with RedditUtils.make_client() as client:
            root = await client.get(
                "/search.rss",
                params={"q": ticker, "t": time_filter, "type": "posts", "limit": 100},
                accept="xml",
                clear_cookies=True,
            )
            all_posts = RedditUtils.parse_posts(root)
            kept      = [p for p in all_posts if p.id in set(post_ids)]

            sem = asyncio.Semaphore(_CONCURRENCY)

            async def _add_comments(post: RedditPost) -> None:
                async with sem:
                    post.comments = await self._fetch_comments(client, post.subreddit, post.id)

            await asyncio.gather(*(_add_comments(p) for p in kept))

        return now_ist(), kept

    @staticmethod
    async def _fetch_comments(client, subreddit: str, post_id: str) -> List[RedditComment]:
        try:
            root = await client.get(
                f"/r/{subreddit}/comments/{post_id}.rss",
                accept="xml",
                clear_cookies=True,
            )
            return RedditUtils.parse_comments(root)
        except ApiError as e:
            logger.warning("comment fetch failed %s/%s: %s", subreddit, post_id, e)
            return []
