"""StocktwitssFetcher — network I/O only, no MCP wiring."""

from __future__ import annotations

from clients.api_client import ApiError
from tools.stocktwits.models import StocktwitsStream
from tools.stocktwits.utils import StocktwitsUtils


class StocktwitssFetcher:
    """Fetches stream data from the Stocktwits public API."""

    async def fetch_stream(self, ticker: str) -> StocktwitsStream:
        """Return a parsed StocktwitsStream for the given ticker."""
        async with StocktwitsUtils.make_client() as client:
            raw_text = await client.get(f"/streams/symbol/{ticker.upper()}.json")
        return StocktwitsUtils.parse_stream(ticker, raw_text)
