# Stock Analysis MCP

[![smithery badge](https://smithery.ai/badge/@SJDev2000/stock-analysis)](https://smithery.ai/server/@SJDev2000/stock-analysis)
[![PyPI version](https://badge.fury.io/py/stock-analysis-mcp.svg)](https://badge.fury.io/py/stock-analysis-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A financial analysis MCP server built on the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python). Provides 8 production-grade tools covering SEC EDGAR fundamentals and real-time social sentiment (Reddit + Stocktwits). Works as a **standalone CLI agent** or as a **Claude Code / Claude Desktop plugin**.

### One-command install (Claude Code)

```bash
claude mcp add stock-analysis -- uvx stock-analysis-mcp
```

Or from the [Smithery marketplace](https://smithery.ai/server/@SJDev2000/stock-analysis):

```bash
npx @smithery/cli install @SJDev2000/stock-analysis --client claude
```

---

## What it does

| Domain | Tools |
|--------|-------|
| **SEC EDGAR** | Income statement, balance sheet, cash flow, company profile — from live XBRL filings |
| **Ratios** | 20+ ratios (ROE, ROIC, FCF margin, D/E, CCC, …) computed from the above |
| **Reddit** | Fetch posts + comment threads via public RSS; two-phase filter-then-fetch |
| **Stocktwits** | Fetch 30 latest messages with labeled sentiment; exponential backoff on rate limits |

Skills in `.claude/skills/` drive report generation — fixed-format markdown templates the agent fills with real numbers. No hallucinated data.

---

## Project structure

```
stock_analysis/
├── run_agent.py              # CLI agent entry point
├── mcp_server.py             # MCP stdio server (plugin entry point)
├── pyproject.toml
├── tools/
│   ├── server.py             # Bundles all tools into one MCP server
│   ├── edgar/                # SEC EDGAR tools (income, balance sheet, cash flow, profile)
│   ├── analysis/             # Financial ratio computation (pure, no I/O)
│   ├── reddit/               # Reddit RSS client + MCP tools
│   └── stocktwits/           # Stocktwits API client + MCP tool
├── .claude/
│   └── skills/               # Report templates (markdown)
│       ├── sentiment-analysis.md       # Reddit + Stocktwits combined report
│       ├── stocktwits-sentiment.md     # Stocktwits-only scorer (forkable child)
│       ├── fundamental-analysis.md     # Full fundamental report
│       ├── income-statement-analysis.md
│       ├── balance-sheet-analysis.md
│       ├── cash-flow-analysis.md
│       └── company-overview.md
└── assets/                   # Generated data (gitignored)
    ├── reddit_sentiment/     # Cached Reddit assets per ticker
    ├── stocktwits/           # Cached Stocktwits streams per ticker
    └── reports/              # Generated analysis reports
```

---

## Install

**Requirements:** Python 3.10+

```bash
git clone https://github.com/your-org/stock-analysis-mcp
cd stock-analysis-mcp
pip install -e .
```

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```ini
# .env
ANTHROPIC_API_KEY=sk-ant-...
REDDIT_USERNAME=your_reddit_username   # for User-Agent header (no auth needed)

# Optional overrides
ANTHROPIC_BASE_URL=
ANTHROPIC_MODEL=us.anthropic.claude-3-7-sonnet-20250219-v1:0
AGENT_REPORTS_DIR=./assets/reports
```

---

## Usage — CLI agent

```bash
# Sentiment analysis (Reddit + Stocktwits)
python run_agent.py "Run sentiment analysis on AAPL"
python run_agent.py "Sentiment analysis on NVDA"

# Fundamental analysis
python run_agent.py "Run fundamental analysis on MSFT"
python run_agent.py "Income statement for GOOGL"
python run_agent.py "Company overview for TSLA"

# Interactive mode
python run_agent.py --interactive

# JSON output (for programmatic use)
python run_agent.py --json "Sentiment analysis on NFLX"

# Options
python run_agent.py --model claude-sonnet-4-5 --max-turns 20 "..."
```

Reports are saved to `assets/reports/` as timestamped markdown files.

### Programmatic API

```python
from run_agent import run, run_async

result = run("Run sentiment analysis on AAPL")
print(result.response)
print(f"Cost: ${result.cost_usd:.4f} | Turns: {result.num_turns}")
print(f"Report: {result.report_path}")
```

---

## Usage — Claude Code / Claude Desktop plugin

The MCP server exposes the full bundle in one connection: **8 tools** (raw data access) and **7 prompts** (skills — invoke with a ticker to run a full structured report).

### Install in Claude Code

**From PyPI (recommended — no git clone needed):**

```bash
claude mcp add stock-analysis -- uvx stock-analysis-mcp
```

`uvx` downloads and runs the package in an isolated environment automatically.
Set your Reddit username (used as the User-Agent header for public RSS):

```bash
claude mcp add stock-analysis -e REDDIT_USERNAME=your_username -- uvx stock-analysis-mcp
```

**From source (development):**

```bash
git clone https://github.com/SJDev2000/stock-analysis
cd stock-analysis
pip install -e .
claude mcp add stock-analysis -- stock-analysis-mcp
```

Once connected, skills appear as slash commands in any Claude Code session:

```
/stock-analysis:sentiment-analysis      → prompts for ticker, runs 11-section report
/stock-analysis:fundamental-analysis    → prompts for ticker, runs full EDGAR report
/stock-analysis:income-statement-analysis
/stock-analysis:balance-sheet-analysis
/stock-analysis:cash-flow-analysis
/stock-analysis:company-overview
/stock-analysis:stocktwits-sentiment
```

Tools are also directly available for raw data access:

```
mcp__stock-analysis__fetch_stocktwits_stream   ticker=AAPL
mcp__stock-analysis__analyze_income_statement  ticker=MSFT
```

### Install in Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "stock-analysis": {
      "command": "python",
      "args": ["/absolute/path/to/stock-analysis/mcp_server.py"],
      "env": {
        "REDDIT_USERNAME": "your_username"
      }
    }
  }
}
```

---

## Tools reference

### SEC EDGAR

| Tool | Description |
|------|-------------|
| `analyze_income_statement` | 5 years annual + 4 quarters, YoY/QoQ growth, segment breakdown, CAGR |
| `analyze_balance_sheet` | Multi-year assets/liabilities/equity, working capital, debt ratios |
| `analyze_cash_flow` | Operating/investing/financing flows, FCF, CapEx intensity, shareholder returns |
| `analyze_company_profile` | CIK, SIC, exchange, business overview, risk factors from 10-K |
| `analyze_financial_ratios` | 20+ ratios from income + balance + cashflow JSON outputs |

### Sentiment

| Tool | Description |
|------|-------------|
| `fetch_reddit_posts` | Phase 1 — post titles/text for relevance filtering (no comments) |
| `fetch_reddit_comments` | Phase 2 — comments for kept posts; saves asset JSON |
| `fetch_stocktwits_stream` | 30 latest messages; labeled (`Bullish`/`Bearish`) + unlabeled; saves asset JSON |

---

## Skills reference

Skills are markdown files in `.claude/skills/` that drive structured report generation. They are loaded automatically by the Claude Agent SDK.

| Skill | Invocation example |
|-------|--------------------|
| `sentiment-analysis` | "Run sentiment analysis on AAPL" |
| `fundamental-analysis` | "Run fundamental analysis on MSFT" |
| `income-statement-analysis` | "Income statement for GOOGL" |
| `balance-sheet-analysis` | "Balance sheet for TSLA" |
| `cash-flow-analysis` | "Cash flow analysis for NFLX" |
| `company-overview` | "Company overview for AMZN" |

The `sentiment-analysis` skill runs with `context: fork` — it executes in an isolated sub-agent, keeping your main conversation thread clean. It fetches and scores both Reddit and Stocktwits, then produces an 11-section combined report with:

- Composite FSS (Reddit 60% + Stocktwits 40%)
- Per-platform signal distribution tables
- Cross-platform divergence analysis
- Labeled vs. inferred sentiment breakdown for Stocktwits
- Trading signal with risk flags

---

## Sentiment scoring

**Reddit scoring:**
- Post: 3× weight | Long comment (≥50 words): 2× | Short comment: 1× | Reply: 0.5×
- Subreddit multiplier: major finance subs 1.0× | other finance 0.8× | non-finance 0.5×

**Stocktwits scoring:**
- Labeled `Bullish` → raw +1.5 | `Bearish` → raw −1.5
- Unlabeled → inferred from text on −2 to +2 scale; long messages 1.5× weight

**Composite FSS** = Reddit FSS × 0.6 + Stocktwits FSS × 0.4

---

## Data sources

| Source | Auth required | Notes |
|--------|--------------|-------|
| SEC EDGAR | No | XBRL filings via [edgar-sec](https://github.com/dgunning/edgartools) |
| Reddit | No | Public RSS feeds |
| Stocktwits | No | Public API — 200 req/hour limit |

All data is sourced live. No fabricated numbers.

---

## License

MIT
