#!/usr/bin/env python3
"""
Stock Analysis MCP Plugin — stdio transport.

Exposes the full bundle as a single MCP server:
  - 8 tools  (SEC EDGAR + sentiment data fetchers)
  - 7 prompts (skills — invoke with a ticker to get a structured analysis)

Install in Claude Code (one command):
    claude mcp add stock-analysis -- python /path/to/mcp_server.py

Install in Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "stock-analysis": {
          "command": "python",
          "args": ["/absolute/path/to/mcp_server.py"],
          "env": { "ANTHROPIC_API_KEY": "...", "REDDIT_USERNAME": "..." }
        }
      }
    }

Once installed, prompts appear in Claude Code as slash commands:
    /stock-analysis:sentiment-analysis     → asks for ticker, runs full report
    /stock-analysis:fundamental-analysis   → asks for ticker, runs full report
    etc.
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ── Skill file resolution (works both in dev and after pip/uvx install) ───────
def _resolve_skills_dir() -> Path:
    # 1. Installed package: importlib.resources (Python 3.9+)
    try:
        from importlib.resources import files
        pkg = files("skills")
        if (pkg / "sentiment-analysis.md").is_file():
            return Path(str(pkg))
    except Exception:
        pass
    # 2. Dev checkout: .claude/skills/ next to this file
    dev_path = Path(__file__).parent.parent / ".claude" / "skills"
    if dev_path.is_dir():
        return dev_path
    raise RuntimeError(
        "Skills directory not found. Run `pip install -e .` in the project root "
        "or ensure .claude/skills/ exists."
    )

import mcp.types as types
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server

# ── Tool function imports ────────────────────────────────────────────────────

from tools.edgar import (
    analyze_income_statement,
    analyze_balance_sheet,
    analyze_cash_flow,
    analyze_company_profile,
)
from tools.analysis import analyze_financial_ratios
from tools.reddit import fetch_reddit_posts, fetch_reddit_comments
from tools.stocktwits import fetch_stocktwits_stream

# ── Skill (prompt) definitions ───────────────────────────────────────────────

_SKILLS_DIR = _resolve_skills_dir()

def _load_skill(filename: str) -> str:
    return (_SKILLS_DIR / filename).read_text(encoding="utf-8")


# Each entry: (prompt_name, title, description, skill_file)
_SKILL_REGISTRY = [
    (
        "sentiment-analysis",
        "Sentiment Analysis",
        "Multi-source sentiment report (Reddit + Stocktwits) for a stock ticker. "
        "Fetches live data, scores labeled and unlabeled messages, and produces an "
        "11-section report with composite FSS, signal distribution, cross-platform "
        "divergence, and a trading signal.",
        "sentiment-analysis.md",
    ),
    (
        "fundamental-analysis",
        "Fundamental Analysis",
        "Full investment-grade fundamental report: income statement, balance sheet, "
        "cash flow, 20+ financial ratios, and an investment scorecard — all sourced "
        "from SEC EDGAR XBRL filings.",
        "fundamental-analysis.md",
    ),
    (
        "income-statement-analysis",
        "Income Statement Analysis",
        "5-year annual + 4-quarter income statement analysis with YoY/QoQ growth, "
        "margin trends, revenue segments, and CAGR — from SEC EDGAR.",
        "income-statement-analysis.md",
    ),
    (
        "balance-sheet-analysis",
        "Balance Sheet Analysis",
        "Multi-year balance sheet covering assets, liabilities, equity, working "
        "capital, debt structure, and key liquidity/leverage ratios.",
        "balance-sheet-analysis.md",
    ),
    (
        "cash-flow-analysis",
        "Cash Flow Analysis",
        "Multi-year operating, investing, and financing cash flows with FCF margin, "
        "CapEx intensity, and capital allocation breakdown.",
        "cash-flow-analysis.md",
    ),
    (
        "company-overview",
        "Company Overview",
        "Company identity, capital structure, business overview, and classified risk "
        "factors extracted from the latest 10-K filing.",
        "company-overview.md",
    ),
    (
        "stocktwits-sentiment",
        "Stocktwits Sentiment",
        "Scores the 30 latest Stocktwits messages for a ticker — labeled and "
        "unlabeled — and returns a compact structured JSON block with FSS, signal "
        "distribution, top themes, and notable messages.",
        "stocktwits-sentiment.md",
    ),
]

_TICKER_ARG = types.PromptArgument(
    name="ticker",
    description="Stock ticker symbol, e.g. AAPL, MSFT, NFLX",
    required=True,
)


def _build_prompt_message(skill_text: str, ticker: str) -> types.PromptMessage:
    """Inject the ticker into the skill body and return a user-role prompt message."""
    content = skill_text.replace("{TICKER}", ticker.upper()).replace("{ticker}", ticker.upper())
    return types.PromptMessage(
        role="user",
        content=types.TextContent(type="text", text=f"Ticker: {ticker.upper()}\n\n{content}"),
    )


# ── MCP tool wrappers ────────────────────────────────────────────────────────
# claude_agent_sdk @tool functions are already async callables that accept a
# dict of args and return an MCP response dict.  We need thin wrappers to adapt
# them to the raw mcp.Server call_tool interface (args arrive as a plain dict).

_SDK_TOOLS = [
    analyze_income_statement,
    analyze_balance_sheet,
    analyze_cash_flow,
    analyze_company_profile,
    analyze_financial_ratios,
    fetch_reddit_posts,
    fetch_reddit_comments,
    fetch_stocktwits_stream,
]

# name → SdkMcpTool
_TOOL_MAP = {t.name: t for t in _SDK_TOOLS}


def _sdk_tool_to_mcp(sdk_tool) -> types.Tool:
    """Convert a claude_agent_sdk SdkMcpTool into an mcp.types.Tool."""
    return types.Tool(
        name=sdk_tool.name,
        description=sdk_tool.description or "",
        inputSchema=sdk_tool.input_schema or {"type": "object", "properties": {}},
    )


# ── Server assembly ──────────────────────────────────────────────────────────

def build_server() -> Server:
    server = Server(
        name="stock-analysis",
        version="1.0.0",
        instructions=(
            "Stock Analysis MCP — 8 tools for SEC EDGAR financial data and "
            "Reddit/Stocktwits sentiment, plus 7 prompt-based analysis skills. "
            "Use the prompts (skills) to run full structured reports by ticker; "
            "use the tools directly for raw data access."
        ),
    )

    # ── Tools ────────────────────────────────────────────────────────────────

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        tools = []
        for sdk_fn in _TOOL_MAP.values():
            try:
                tools.append(_sdk_tool_to_mcp(sdk_fn))
            except Exception:
                # Fallback: minimal tool definition
                name = getattr(sdk_fn, "_tool_name", sdk_fn.__name__)
                tools.append(types.Tool(
                    name=name,
                    description=getattr(sdk_fn, "_tool_description", ""),
                    inputSchema={"type": "object", "properties": {}},
                ))
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        sdk_tool = _TOOL_MAP.get(name)
        if sdk_tool is None:
            raise ValueError(f"Unknown tool: {name}")
        result = await sdk_tool.handler(arguments)
        # SDK tools return {"content": [{"type": "text", "text": "..."}], ...}
        content_blocks = result.get("content", [])
        return [
            types.TextContent(type="text", text=block.get("text", ""))
            for block in content_blocks
            if block.get("type") == "text"
        ]

    # ── Prompts (skills) ─────────────────────────────────────────────────────

    _prompts: list[types.Prompt] = [
        types.Prompt(
            name=name,
            title=title,
            description=description,
            arguments=[_TICKER_ARG],
        )
        for name, title, description, _ in _SKILL_REGISTRY
    ]

    _skill_text: dict[str, str] = {
        name: _load_skill(filename)
        for name, _, _, filename in _SKILL_REGISTRY
    }

    @server.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        return _prompts

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        skill_text = _skill_text.get(name)
        if skill_text is None:
            raise ValueError(f"Unknown prompt: {name}")
        ticker = (arguments or {}).get("ticker", "TICKER")
        return types.GetPromptResult(
            description=next(
                (desc for n, _, desc, _ in _SKILL_REGISTRY if n == name), ""
            ),
            messages=[_build_prompt_message(skill_text, ticker)],
        )

    return server


# ── Entry points ─────────────────────────────────────────────────────────────

async def main() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main_sync() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
