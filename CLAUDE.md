# Stock Analysis

SEC EDGAR financial data and Reddit/Stocktwits sentiment analysis toolkit.

## Skills

Project-level skills are in `.claude/skills/`:

- `/fundamental-analysis <TICKER>` — Full investment-grade report (runs all three analysts + ratios)
- `/income-statement <artifact_path>` — Income statement report (called by income-statement-analyst agent)
- `/balance-sheet <artifact_path>` — Balance sheet report (called by balance-sheet-analyst agent)
- `/cash-flow <artifact_path>` — Cash flow report (called by cash-flow-analyst agent)
- `/sentiment-analysis <TICKER>` — Reddit + Stocktwits combined sentiment report
- `/reddit-sentiment <artifact_path>` — Reddit scoring (called by reddit-analyst agent)
- `/stocktwits-sentiment <artifact_path>` — Stocktwits scoring (called by stocktwits-analyst agent)
- `/company-overview <TICKER>` — Company profile, business overview, risk factors

## Agents

Project-level agents are in `.claude/agents/`:

- `income-statement-analyst` — Fetches income statement data, passes asset_path to income-statement skill
- `balance-sheet-analyst` — Fetches balance sheet data, passes asset_path to balance-sheet skill
- `cash-flow-analyst` — Fetches cash flow data, passes asset_path to cash-flow skill
- `reddit-analyst` — Fetches Reddit posts, passes asset_path to reddit-sentiment skill
- `stocktwits-analyst` — Fetches Stocktwits stream, passes asset_path to stocktwits-sentiment skill
