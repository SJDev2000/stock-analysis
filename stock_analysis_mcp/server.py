"""
Stock Analysis MCP Server — stdio transport.

Exposes:
  - 8 tools  : SEC EDGAR financial data + Reddit/Stocktwits sentiment fetchers
  - 3 prompts: sentiment-analysis, fundamental-analysis, company-overview

Install via uvx (no local checkout needed):
    uvx stock-analysis-mcp

JSON config for Cline / Claude Desktop / any MCP client:
    {
      "mcpServers": {
        "stock-analysis": {
          "command": "uvx",
          "args": ["stock-analysis-mcp"],
          "env": { "REDDIT_USERNAME": "your_username" }
        }
      }
    }
"""

import asyncio
import logging
import typing
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import mcp.types as types
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server

from tools.edgar import (
    analyze_income_statement,
    analyze_balance_sheet,
    analyze_cash_flow,
    analyze_company_profile,
    analyze_financial_ratios,
)
from tools.reddit import fetch_reddit_posts, fetch_reddit_comments
from tools.stocktwits import fetch_stocktwits_stream

logger = logging.getLogger(__name__)

# ── Skills directory ──────────────────────────────────────────────────────────

def _find_skills_dir() -> Path:
    """Locate the skills package — installed wheel or dev checkout."""
    # 1. Installed package: skills/ is a proper package on sys.path
    try:
        from importlib.resources import files
        pkg = files("skills")
        if (pkg / "sentiment-analysis.md").is_file():
            return Path(str(pkg))
    except Exception:
        pass
    # 2. Dev checkout: .claude/skills/ alongside this file's grandparent
    dev = Path(__file__).parent.parent / ".claude" / "skills"
    if dev.is_dir():
        return dev
    raise RuntimeError(
        "Skills package not found. Run `pip install stock-analysis-mcp` or `pip install -e .`"
    )

_SKILLS_DIR = _find_skills_dir()


def _load_skill(filename: str) -> str:
    return (_SKILLS_DIR / filename).read_text(encoding="utf-8")


# ── Prompt registry ───────────────────────────────────────────────────────────
# Only these 3 are exposed to the user via list_prompts.
# Other skill files (income-statement-analysis, balance-sheet-analysis,
# cash-flow-analysis, stocktwits-sentiment) are used internally.

_USER_PROMPTS: list[tuple[str, str, str, str]] = [
    # (name, title, description, skill_file)
    (
        "sentiment-analysis",
        "Sentiment Analysis",
        "Multi-source sentiment report (Reddit + Stocktwits) for a stock ticker. "
        "Fetches live data, scores labeled and unlabeled messages, and produces a "
        "structured report with composite FSS, signal distribution, cross-platform "
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
        "company-overview",
        "Company Overview",
        "Company identity, capital structure, business overview, and classified risk "
        "factors extracted from the latest 10-K filing on SEC EDGAR.",
        "company-overview.md",
    ),
]

_TICKER_ARG = types.PromptArgument(
    name="ticker",
    description="Stock ticker symbol, e.g. AAPL, MSFT, NFLX",
    required=True,
)

_PROMPTS: list[types.Prompt] = [
    types.Prompt(name=name, title=title, description=desc, arguments=[_TICKER_ARG])
    for name, title, desc, _ in _USER_PROMPTS
]

_SKILL_TEXT: dict[str, str] = {
    name: _load_skill(filename)
    for name, _, _, filename in _USER_PROMPTS
}


def _render_prompt(skill_text: str, ticker: str) -> types.PromptMessage:
    """Inject ticker into skill body and return a user-role prompt message."""
    body = skill_text.replace("{TICKER}", ticker.upper()).replace("{ticker}", ticker.upper())
    return types.PromptMessage(
        role="user",
        content=types.TextContent(type="text", text=f"Ticker: {ticker.upper()}\n\n{body}"),
    )


# ── Tool registry ─────────────────────────────────────────────────────────────

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

_TOOL_MAP: dict[str, object] = {t.name: t for t in _SDK_TOOLS}

_PY_TO_JSON_TYPE = {
    int: "integer",
    float: "number",
    bool: "boolean",
    str: "string",
    list: "array",
}


def _build_json_schema(raw: dict) -> dict:
    """Convert Annotated-type dict (from claude_agent_sdk) to JSON Schema object."""
    properties: dict = {}
    required: list = []
    for param, annotation in raw.items():
        if typing.get_origin(annotation) is typing.Annotated:
            args = annotation.__args__
            base_type = args[0]
            description = next((a for a in args[1:] if isinstance(a, str)), "")
            if typing.get_origin(base_type) is list:
                item_py = getattr(base_type, "__args__", (str,))[0]
                prop: dict = {"type": "array", "items": {"type": _PY_TO_JSON_TYPE.get(item_py, "string")}}
            else:
                prop = {"type": _PY_TO_JSON_TYPE.get(base_type, "string")}
            if description:
                prop["description"] = description
        else:
            prop = annotation if isinstance(annotation, dict) else {"type": "string"}
        properties[param] = prop
        required.append(param)
    return {"type": "object", "properties": properties, "required": required}


def _tool_schema(sdk_tool) -> dict:
    raw = sdk_tool.input_schema or {}
    if raw and "properties" not in raw:
        return _build_json_schema(raw)
    return raw or {"type": "object", "properties": {}}


_COERCE: dict = {
    "integer": int,
    "number": float,
    "boolean": lambda v: v if isinstance(v, bool) else str(v).lower() not in ("false", "0", ""),
    "string": str,
}


def _coerce_args(arguments: dict, sdk_tool) -> dict:
    """Coerce string arguments from MCP to the types declared in the tool schema."""
    props = _tool_schema(sdk_tool).get("properties", {})
    result = dict(arguments)
    for key, val in arguments.items():
        json_type = props.get(key, {}).get("type")
        coercer = _COERCE.get(json_type)
        if coercer and not isinstance(val, (int, float, bool, list, dict)):
            try:
                result[key] = coercer(val)
            except (ValueError, TypeError):
                pass
    return result


# ── Server ────────────────────────────────────────────────────────────────────

def build_server() -> Server:
    server = Server(
        name="stock-analysis",
        version="1.0.4",
        instructions=(
            "Stock Analysis MCP — 8 tools for SEC EDGAR financial data and "
            "Reddit/Stocktwits sentiment. Use the 3 prompts (sentiment-analysis, "
            "fundamental-analysis, company-overview) to run full structured reports "
            "by ticker; use tools directly for raw data access."
        ),
    )

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        tools = []
        for sdk_fn in _TOOL_MAP.values():
            try:
                schema = _tool_schema(sdk_fn)
                tools.append(types.Tool(
                    name=sdk_fn.name,
                    description=sdk_fn.description or "",
                    inputSchema=schema,
                ))
            except Exception:
                logger.exception("Failed to build schema for tool %s", getattr(sdk_fn, "name", "?"))
                tools.append(types.Tool(
                    name=getattr(sdk_fn, "name", sdk_fn.__name__),
                    description=getattr(sdk_fn, "description", ""),
                    inputSchema={"type": "object", "properties": {}},
                ))
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        sdk_tool = _TOOL_MAP.get(name)
        if sdk_tool is None:
            raise ValueError(f"Unknown tool: {name!r}")
        try:
            coerced = _coerce_args(arguments, sdk_tool)
            result = await sdk_tool.handler(coerced)
            return [
                types.TextContent(type="text", text=block.get("text", ""))
                for block in result.get("content", [])
                if block.get("type") == "text"
            ]
        except Exception as exc:
            logger.exception("Tool %r failed", name)
            return [types.TextContent(type="text", text=f"Error in {name}: {exc}")]

    @server.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        return _PROMPTS

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        skill_text = _SKILL_TEXT.get(name)
        if skill_text is None:
            raise ValueError(f"Unknown prompt: {name!r}")
        ticker = (arguments or {}).get("ticker", "TICKER")
        description = next((desc for n, _, desc, _ in _USER_PROMPTS if n == name), "")
        return types.GetPromptResult(
            description=description,
            messages=[_render_prompt(skill_text, ticker)],
        )

    return server


# ── Entry points ──────────────────────────────────────────────────────────────

async def _run() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
