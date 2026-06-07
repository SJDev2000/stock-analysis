"""MCP tool for Stocktwits stream data."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Dict

from claude_agent_sdk import tool

from tools.stocktwits.fetcher import StocktwitssFetcher
from tools.stocktwits.utils import StocktwitsUtils

logger   = logging.getLogger(__name__)
_fetcher = StocktwitssFetcher()


@tool(
    "fetch_stocktwits_stream",
    "Fetch the 30 most recent Stocktwits messages for a stock ticker. "
    "Saves the stream to artifacts/stocktwits/{TICKER}_stream.json and returns "
    "the asset path plus a compact summary. Each message includes body text, "
    "timestamp, username, and sentiment_label ('Bullish'|'Bearish'|null for unlabeled). "
    "Use this as the first step in Stocktwits sentiment analysis.",
    {
        "ticker": Annotated[str, "Stock ticker symbol, e.g. 'AAPL', 'NFLX'"],
    },
)
async def fetch_stocktwits_stream(args: Dict[str, Any]) -> Dict[str, Any]:
    ticker = str(args.get("ticker", "")).upper().strip()

    if not ticker:
        return StocktwitsUtils.err_response("ticker is required")

    try:
        stream = await _fetcher.fetch_stream(ticker)
    except Exception as e:
        logger.exception("fetch_stocktwits_stream failed for %s", ticker)
        return StocktwitsUtils.err_response(str(e), ticker=ticker)

    path = StocktwitsUtils.asset_path(ticker)
    StocktwitsUtils.save_asset(path, stream)

    summary = StocktwitsUtils.stream_summary(stream)
    return StocktwitsUtils.ok_response({
        "success":     True,
        "ticker":      stream.ticker,
        "report_type": "stocktwits_stream",
        "fetched_at":  stream.fetched_at,
        "asset_path":  str(path),
        **summary,
    })
