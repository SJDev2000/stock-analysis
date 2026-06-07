"""
MCP Server Registry — Bundles tools into named servers.

Each server groups tools by data domain. The Claude Agent SDK
routes tool calls to the appropriate in-process server.

Servers:
    edgar — SEC EDGAR financial data + ratio analysis
"""

from claude_agent_sdk import create_sdk_mcp_server

from tools.edgar import (
    analyze_income_statement,
    analyze_balance_sheet,
    analyze_cash_flow,
    analyze_company_profile,
)
from tools.analysis import analyze_financial_ratios
from tools.reddit import fetch_reddit_posts, fetch_reddit_comments
from tools.stocktwits import fetch_stocktwits_stream

edgar_server = create_sdk_mcp_server(
    name="edgar",
    version="3.0.0",
    tools=[
        # Data tools (network I/O)
        analyze_income_statement,
        analyze_balance_sheet,
        analyze_cash_flow,
        analyze_company_profile,
        # Analysis tools (pure computation)
        analyze_financial_ratios,
        # Reddit sentiment data
        fetch_reddit_posts,
        fetch_reddit_comments,
        # Stocktwits sentiment data
        fetch_stocktwits_stream,
    ],
)
