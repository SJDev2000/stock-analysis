from claude_agent_sdk import create_sdk_mcp_server

from tools.edgar import (
    analyze_income_statement,
    analyze_balance_sheet,
    analyze_cash_flow,
    analyze_company_profile,
    analyze_financial_ratios,
)
from tools.reddit import fetch_reddit_posts, fetch_reddit_comments
from tools.stocktwits import fetch_stocktwits_stream

edgar_server = create_sdk_mcp_server(
    name="edgar",
    version="4.0.0",
    tools=[
        analyze_income_statement,
        analyze_balance_sheet,
        analyze_cash_flow,
        analyze_company_profile,
        analyze_financial_ratios,
        fetch_reddit_posts,
        fetch_reddit_comments,
        fetch_stocktwits_stream,
    ],
)
