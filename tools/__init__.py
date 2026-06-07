"""
Tools — In-process MCP servers for stock analysis.

Organized by data source and function:

    tools/edgar/       DATA tools — fetch from SEC EDGAR (network I/O)
    tools/analysis/    ANALYSIS tools — pure computation (no I/O)

Future teams will add their own tool packages:
    tools/market/      Market data (prices, volume, options)
    tools/news/        News & sentiment (RSS, NLP)
    tools/execution/   Order execution (broker APIs)
"""

from tools.server import edgar_server

__all__ = ["edgar_server"]

# Reddit sentiment tools available directly:
#   from tools.reddit import fetch_ticker_tree, poll_ticker_tree, TickerTree
