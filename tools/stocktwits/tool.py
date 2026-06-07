"""MCP tool for Stocktwits stream data."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

from claude_agent_sdk import tool

from tools.stocktwits.client import StocktwitsClient
from tools.stocktwits.models import StocktwitsMessage, StocktwitsStream

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).parent.parent.parent / "assets" / "stocktwits"

_client: Optional[StocktwitsClient] = None


def _get_client() -> StocktwitsClient:
    global _client
    if _client is None:
        _client = StocktwitsClient()
    return _client


def _err(msg: str) -> Dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps({"success": False, "error": msg})}],
        "is_error": True,
    }


def _asset_path(ticker: str) -> Path:
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    return _ASSETS_DIR / f"{ticker.upper()}_stream.json"


def _parse_stream(ticker: str, data: Dict[str, Any]) -> StocktwitsStream:
    fetched_at = datetime.now(tz=timezone.utc).strftime("%-d %B %Y %-I:%M %p UTC")
    messages = []
    for raw in data.get("messages", []):
        entities = raw.get("entities", {})
        sentiment_node = entities.get("sentiment")
        sentiment_label: Optional[str] = None
        if isinstance(sentiment_node, dict):
            sentiment_label = sentiment_node.get("basic")  # "Bullish" | "Bearish" | None

        messages.append(StocktwitsMessage(
            id=raw["id"],
            body=raw.get("body", ""),
            created_at=raw.get("created_at", ""),
            username=raw.get("user", {}).get("username", "unknown"),
            sentiment_label=sentiment_label,
        ))
    return StocktwitsStream(ticker=ticker.upper(), fetched_at=fetched_at, messages=messages)


@tool(
    "fetch_stocktwits_stream",
    (
        "Fetch the 30 most recent Stocktwits messages for a stock ticker. "
        "Saves the stream to assets/stocktwits/{TICKER}_stream.json and returns "
        "the asset path plus a compact summary. Each message includes body text, "
        "timestamp, username, and sentiment_label ('Bullish'|'Bearish'|null for unlabeled). "
        "Use this as the first step in Stocktwits sentiment analysis."
    ),
    {
        "ticker": Annotated[str, "Stock ticker symbol, e.g. 'AAPL', 'NFLX'"],
    },
)
async def fetch_stocktwits_stream(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker = str(args.get("ticker", "")).upper().strip()

    if not ticker:
        return _err("ticker is required")

    try:
        data = await _get_client().get_symbol_stream(ticker)
    except Exception as e:
        logger.exception("fetch_stocktwits_stream failed for %s", ticker)
        return _err(str(e))

    stream = _parse_stream(ticker, data)

    asset_path = _asset_path(ticker)
    asset_path.write_text(stream.to_json())

    labeled = sum(1 for m in stream.messages if m.sentiment_label is not None)
    unlabeled = len(stream.messages) - labeled
    bullish = sum(1 for m in stream.messages if m.sentiment_label == "Bullish")
    bearish = sum(1 for m in stream.messages if m.sentiment_label == "Bearish")

    result = {
        "success": True,
        "ticker": stream.ticker,
        "fetched_at": stream.fetched_at,
        "message_count": len(stream.messages),
        "labeled_count": labeled,
        "unlabeled_count": unlabeled,
        "bullish_labeled": bullish,
        "bearish_labeled": bearish,
        "asset_path": str(asset_path),
    }
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]}
