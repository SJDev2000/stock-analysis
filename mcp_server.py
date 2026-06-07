#!/usr/bin/env python3
"""
Stock Analysis MCP Server — stdio transport.

Exposes all tools over the MCP stdio protocol so any MCP host
(Claude Code, Claude Desktop, etc.) can install this as a plugin.

Usage (direct):
    python mcp_server.py

Claude Code installation:
    claude mcp add stock-analysis -- python /path/to/mcp_server.py

Claude Desktop installation (claude_desktop_config.json):
    {
      "mcpServers": {
        "stock-analysis": {
          "command": "python",
          "args": ["/path/to/mcp_server.py"]
        }
      }
    }
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path so tools/ is importable
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from mcp.server.stdio import stdio_server
from tools.edgar import (
    analyze_income_statement,
    analyze_balance_sheet,
    analyze_cash_flow,
    analyze_company_profile,
)
from tools.analysis import analyze_financial_ratios
from tools.reddit import fetch_reddit_posts, fetch_reddit_comments
from tools.stocktwits import fetch_stocktwits_stream
from claude_agent_sdk import create_sdk_mcp_server

_server = create_sdk_mcp_server(
    name="stock-analysis",
    version="1.0.0",
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


async def main() -> None:
    instance = _server["instance"]
    async with stdio_server() as (read_stream, write_stream):
        await instance.run(read_stream, write_stream, instance.create_initialization_options())


def main_sync() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
