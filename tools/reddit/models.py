from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RedditComment:
    body: str
    created_ist: str


@dataclass
class RedditPost:
    id: str
    subreddit: str
    title: str
    selftext: str
    url: str
    created_ist: str
    comments: List[RedditComment] = field(default_factory=list)
