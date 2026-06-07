"""StocktwitsUtils — stateless helpers for Stocktwits parsing and MCP response building."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from clients.api_client import ApiClient
from tools.stocktwits.models import StocktwitsMessage, StocktwitsStream
from common_utilities import now_utc_label

_ASSETS_DIR = Path(__file__).parent.parent.parent / "artifacts" / "stocktwits"
_BASE_URL   = "https://api.stocktwits.com/api/2"


class StocktwitsUtils:
    """Stateless helpers — call as class methods."""

    # ------------------------------------------------------------------ #
    # HTTP client factory                                                  #
    # ------------------------------------------------------------------ #

    @staticmethod
    def make_client() -> ApiClient:
        return ApiClient(
            base_url=_BASE_URL,
            headers={"User-Agent": "stock-analysis-agent/1.0"},
        )

    # ------------------------------------------------------------------ #
    # Asset persistence                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def asset_path(ticker: str) -> Path:
        _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        return _ASSETS_DIR / f"{ticker.upper()}_stocktwits_stream.json"

    @staticmethod
    def save_asset(path: Path, stream: StocktwitsStream) -> None:
        # Overwrite any previous run — only one file per ticker
        path.unlink(missing_ok=True)
        path.write_text(stream.to_json())

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
    # Stream parsing                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def parse_stream(ticker: str, raw_text: str) -> StocktwitsStream:
        data = json.loads(raw_text)
        messages = []
        for raw in data.get("messages", []):
            sentiment_node = raw.get("entities", {}).get("sentiment")
            label: Optional[str] = sentiment_node.get("basic") if isinstance(sentiment_node, dict) else None
            messages.append(StocktwitsMessage(
                id              = raw["id"],
                body            = raw.get("body", ""),
                created_at      = raw.get("created_at", ""),
                username        = raw.get("user", {}).get("username", "unknown"),
                sentiment_label = label,
            ))
        return StocktwitsStream(ticker=ticker.upper(), fetched_at=now_utc_label(), messages=messages)

    # ------------------------------------------------------------------ #
    # Summary builder                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def stream_summary(stream: StocktwitsStream) -> Dict[str, Any]:
        labeled  = [m for m in stream.messages if m.sentiment_label is not None]
        bullish  = sum(1 for m in labeled if m.sentiment_label == "Bullish")
        bearish  = sum(1 for m in labeled if m.sentiment_label == "Bearish")
        return {
            "message_count":   len(stream.messages),
            "labeled_count":   len(labeled),
            "unlabeled_count": len(stream.messages) - len(labeled),
            "bullish_count":   bullish,
            "bearish_count":   bearish,
        }
