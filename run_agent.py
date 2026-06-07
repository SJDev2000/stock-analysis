#!/usr/bin/env python3
"""
Stock Analysis Agent — Skills-driven architecture.

The Claude Agent SDK loads skills from .claude/skills/ which define
what tools to call and how to format reports. No agent definitions needed.

Usage:
    python run_agent.py "Run fundamental analysis on AAPL"
    python run_agent.py "Analyze MSFT income statement"
    python run_agent.py --interactive
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
load_dotenv()

import anyio

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    ClaudeSDKClient,
    TextBlock,
    query,
)

from claude_agent_sdk.types import ThinkingConfigAdaptive
from tools.server import edgar_server


REPORTS_DIR = Path(os.getenv(
    "AGENT_REPORTS_DIR",
    Path(__file__).parent / "assets" / "reports",
))


@dataclass
class RunResult:
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0
    num_turns: int = 0
    cost_usd: Optional[float] = None
    report_path: Optional[str] = None
    section_reports: Dict[str, str] = field(default_factory=dict)


def _build_options(
    model: Optional[str] = None,
    max_turns: Optional[int] = None,
    stream: bool = True,
) -> ClaudeAgentOptions:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")
    default_model = os.getenv("ANTHROPIC_MODEL", "us.anthropic.claude-sonnet-4-6")

    env = {"ANTHROPIC_API_KEY": api_key}
    if base_url:
        env["ANTHROPIC_BASE_URL"] = base_url
    reddit_username = os.getenv("REDDIT_USERNAME", "")
    if reddit_username:
        env["REDDIT_USERNAME"] = reddit_username

    system_prompt = (
        "You are a stock analysis assistant. "
        "For every user request, extract the ticker symbol and determine which analysis to run:\n"
        "- If the request mentions 'sentiment', 'reddit', 'stocktwits', 'social', or 'crowd': "
        "invoke Skill(skill='sentiment-analysis', args='<TICKER>').\n"
        "- If the request mentions 'fundamental', 'financials', 'income', 'balance sheet', 'cash flow', or 'earnings': "
        "invoke Skill(skill='fundamental-analysis', args='<TICKER>').\n"
        "- If the request mentions both (or asks for a 'full' or 'complete' analysis): "
        "invoke both skills in sequence — fundamental-analysis first, then sentiment-analysis.\n"
        "- If no clear category is specified, default to fundamental-analysis.\n"
        "Do not answer from memory, do not generate free-form text, do not call any tools directly. "
        "Your only actions are to invoke the appropriate skill(s)."
    )

    return ClaudeAgentOptions(
        model=model or default_model,
        max_turns=max_turns or 30,
        mcp_servers={"edgar": edgar_server},
        allowed_tools=[
            "Skill",
            "Agent",
            "mcp__stock-analysis__*",
            "mcp__edgar__*",
        ],
        permission_mode="acceptEdits",
        env=env,
        thinking=ThinkingConfigAdaptive(type="adaptive"),
        effort="high",
        include_partial_messages=stream,
        cwd=str(Path(__file__).parent),
        skills=[
            "fundamental-analysis",
            "income-statement",
            "balance-sheet",
            "cash-flow",
            "sentiment-analysis",
            "reddit-sentiment",
            "stocktwits-sentiment",
            "company-overview",
        ],
        system_prompt=system_prompt,
    )


# ---------------------------------------------------------------------------
# Report saving
# ---------------------------------------------------------------------------

def _detect_source(prompt: str, content: str) -> str:
    p = prompt.lower()
    if any(k in p for k in ("sentiment", "reddit", "stocktwits")):
        return "Reddit RSS (public feeds) | Stocktwits Public API"
    return "SEC EDGAR (10-K / 10-Q XBRL)"


def _fmt_report(content: str, prompt: str, section: Optional[str] = None) -> str:
    ts = datetime.now(tz=timezone.utc)
    source = _detect_source(prompt, content)
    lines = ["---"]
    lines.append(f"generated_at: {ts.isoformat(timespec='seconds')}")
    if section:
        lines.append(f"section: {section}")
    lines.append(f'prompt: "{prompt[:100]}"')
    lines.append(f"source: {source}")
    lines.append("---")
    lines.append("")
    lines.append(content)
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated: {ts.strftime('%Y-%m-%d %H:%M UTC')} | Source: {source}*")
    lines.append("")
    return "\n".join(lines)


def _split_sections(response: str) -> Dict[str, str]:
    markers = [
        ("income_statement", ["income statement", "revenue & profitability", "section 2: income"]),
        ("balance_sheet", ["balance sheet", "assets & liabilities", "section 3: balance", "financial position"]),
        ("cash_flow", ["cash flow", "free cash flow", "section 4: cash"]),
        ("financial_ratios", ["financial ratio", "ratio dashboard", "section 5:", "key ratios"]),
        ("scorecard", ["investment scorecard", "overall assessment", "section 6", "section 7", "verdict"]),
    ]

    sections = {}
    lines = response.split("\n")
    current = None
    buf: list = []

    for line in lines:
        low = line.lower().strip()
        if low.startswith("#"):
            detected = None
            for name, keywords in markers:
                if any(k in low for k in keywords):
                    detected = name
                    break
            if detected and detected != current:
                if current and buf:
                    sections[current] = "\n".join(buf)
                current = detected
                buf = [line]
                continue
        if current:
            buf.append(line)

    if current and buf:
        sections[current] = "\n".join(buf)

    return sections


def _save_reports(response: str, prompt: str) -> tuple[Optional[str], Dict[str, str]]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc)
    date_str = ts.strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower().strip())[:40].strip("_")

    sections = _split_sections(response)

    if sections:
        report_dir = REPORTS_DIR / f"{date_str}_{slug}"
        report_dir.mkdir(parents=True, exist_ok=True)

        parent_path = report_dir / "00_full_report.md"
        parent_path.write_text(_fmt_report(response, prompt))

        saved = {}
        order = ["income_statement", "balance_sheet", "cash_flow", "financial_ratios", "scorecard"]
        idx = 1
        for name in order:
            if name in sections:
                path = report_dir / f"{idx:02d}_{name}.md"
                path.write_text(_fmt_report(sections[name], prompt, name))
                saved[name] = str(path)
                idx += 1
        for name, text in sections.items():
            if name not in saved:
                path = report_dir / f"{idx:02d}_{name}.md"
                path.write_text(_fmt_report(text, prompt, name))
                saved[name] = str(path)
                idx += 1

        return str(parent_path), saved
    else:
        path = REPORTS_DIR / f"{date_str}_{slug}.md"
        path.write_text(_fmt_report(response, prompt))
        return str(path), {}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def _print_status(msg: str):
    sys.stderr.write(f"\033[90m{msg}\033[0m\n")
    sys.stderr.flush()


def _extract_text(message: AssistantMessage) -> str:
    text = ""
    for block in message.content:
        if isinstance(block, TextBlock):
            text += block.text
        elif isinstance(block, dict):
            if block.get("type") == "text":
                text += block.get("text", "")
            elif block.get("type") == "tool_use":
                _print_status(f"  -> {block.get('name', 'tool')}...")
        elif hasattr(block, "text"):
            text += block.text
    return text


async def _run_query(prompt: str, options: ClaudeAgentOptions, stream: bool = True) -> RunResult:
    response_text = ""
    result_msg: Optional[ResultMessage] = None

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                chunk = _extract_text(message)
                if chunk:
                    if stream:
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                    response_text += chunk
            elif isinstance(message, ResultMessage):
                result_msg = message
    except Exception as e:
        if response_text:
            if stream:
                sys.stdout.write("\n")
            report_path, section_reports = _save_reports(response_text, prompt)
            return RunResult(success=True, response=response_text, report_path=report_path, section_reports=section_reports)
        return RunResult(success=False, error=str(e))

    if stream and response_text:
        sys.stdout.write("\n")
        sys.stdout.flush()

    if result_msg is None:
        if response_text:
            report_path, section_reports = _save_reports(response_text, prompt)
            return RunResult(success=True, response=response_text, report_path=report_path, section_reports=section_reports)
        return RunResult(success=False, error="No result received")

    if result_msg.is_error and result_msg.subtype != "success":
        return RunResult(
            success=False,
            error=result_msg.result or "; ".join(result_msg.errors or []) or "Failed",
            duration_ms=result_msg.duration_ms,
            num_turns=result_msg.num_turns,
            cost_usd=result_msg.total_cost_usd,
        )

    final_text = result_msg.result or response_text
    report_path, section_reports = _save_reports(final_text, prompt) if final_text else (None, {})

    return RunResult(
        success=True,
        response=final_text,
        duration_ms=result_msg.duration_ms,
        num_turns=result_msg.num_turns,
        cost_usd=result_msg.total_cost_usd,
        report_path=report_path,
        section_reports=section_reports,
    )


def run(prompt: str, model: Optional[str] = None, max_turns: Optional[int] = None, stream: bool = True) -> RunResult:
    options = _build_options(model=model, max_turns=max_turns, stream=stream)
    return anyio.run(_run_query, prompt, options, stream)


async def run_async(prompt: str, model: Optional[str] = None, max_turns: Optional[int] = None, stream: bool = True) -> RunResult:
    options = _build_options(model=model, max_turns=max_turns, stream=stream)
    return await _run_query(prompt, options, stream)


async def _interactive(model: Optional[str] = None, max_turns: Optional[int] = None):
    options = _build_options(model=model, max_turns=max_turns, stream=True)

    async with ClaudeSDKClient(options=options) as client:
        print("Stock Analysis Agent (type 'quit' to exit)")
        print("-" * 50)
        while True:
            try:
                prompt = input("\n> ")
            except (EOFError, KeyboardInterrupt):
                break
            if prompt.strip().lower() in ("quit", "exit", "q"):
                break
            if not prompt.strip():
                continue

            await client.query(prompt)
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    chunk = _extract_text(message)
                    if chunk:
                        print(chunk, end="", flush=True)
                elif isinstance(message, ResultMessage):
                    if message.total_cost_usd:
                        print(f"\n[cost: ${message.total_cost_usd:.4f} | turns: {message.num_turns}]")
                    break
            print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Stock Analysis Agent")
    parser.add_argument("prompt", nargs="*", help="Natural language prompt")
    parser.add_argument("--interactive", "-i", action="store_true")
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-turns", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-stream", action="store_true")

    args = parser.parse_args()

    if args.interactive:
        anyio.run(_interactive, args.model, args.max_turns)
        return

    if not args.prompt:
        parser.print_help()
        return

    prompt = " ".join(args.prompt)
    stream = not (args.json or args.no_stream)
    result = run(prompt, model=args.model, max_turns=args.max_turns, stream=stream)

    if args.json:
        print(json.dumps({
            "success": result.success,
            "response": result.response,
            "duration_ms": result.duration_ms,
            "num_turns": result.num_turns,
            "cost_usd": result.cost_usd,
            "report_path": result.report_path,
            "section_reports": result.section_reports,
            **({"error": result.error} if result.error else {}),
        }, indent=2, default=str))
    else:
        if result.success:
            if result.report_path:
                print(f"\nReport: {result.report_path}", file=sys.stderr)
            if result.section_reports:
                for name, path in result.section_reports.items():
                    print(f"  {name}: {path}", file=sys.stderr)
            if result.cost_usd:
                print(f"Cost: ${result.cost_usd:.4f} | Turns: {result.num_turns}", file=sys.stderr)
        else:
            print(f"Error: {result.error}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
