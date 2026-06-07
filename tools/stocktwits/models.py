from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StocktwitsMessage:
    id: int
    body: str
    created_at: str
    username: str
    # Stocktwits labels: "Bullish" | "Bearish" | None (unlabeled)
    sentiment_label: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "body": self.body,
            "created_at": self.created_at,
            "username": self.username,
            "sentiment_label": self.sentiment_label,
        }


@dataclass
class StocktwitsStream:
    ticker: str
    fetched_at: str
    messages: List[StocktwitsMessage] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "fetched_at": self.fetched_at,
            "message_count": len(self.messages),
            "messages": [m.to_dict() for m in self.messages],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
