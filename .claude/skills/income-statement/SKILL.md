---
name: income-statement
description: Presentation skill — income statement. Receives artifact asset_path in {args}, reads JSON, renders structured report template.
tools:
  - Bash
  - Read
---

Read the artifact at `{args}` using the Read tool, then fill every cell in the template below with real data from that file. Output only the completed template — no preamble, no commentary, no extra sections.

Rules: $B (1dp) if ≥$1B, else $M. Margins 1dp. EPS 2dp. Growth rates with sign (+/-). N/R for null. No emoji.

---

# {COMPANY_NAME} ({TICKER}) — Income Statement Analysis
**Source:** SEC EDGAR 10-K / 10-Q XBRL filings
**Coverage:** {N} fiscal years + {N} recent quarters

---

## Section 1: Financial Summary Table

### Annual

| Metric             | FY{Y1} | FY{Y2} | FY{Y3} | FY{Y4} | FY{Y5} |
|--------------------|--------|--------|--------|--------|--------|
| Revenue            |        |        |        |        |        |
| Cost of Revenue    |        |        |        |        |        |
| Gross Profit       |        |        |        |        |        |
| Gross Margin %     |        |        |        |        |        |
| Operating Income   |        |        |        |        |        |
| Operating Margin % |        |        |        |        |        |
| Net Income         |        |        |        |        |        |
| Net Margin %       |        |        |        |        |        |
| EPS (Diluted)      |        |        |        |        |        |
| EBITDA             |        |        |        |        |        |

### Quarterly

| Metric             | Q{Q1} | Q{Q2} | Q{Q3} | Q{Q4} |
|--------------------|-------|-------|-------|-------|
| Revenue            |       |       |       |       |
| Gross Profit       |       |       |       |       |
| Gross Margin %     |       |       |       |       |
| Operating Income   |       |       |       |       |
| Net Income         |       |       |       |       |
| EPS (Diluted)      |       |       |       |       |

---

## Section 2: Growth Trajectory

### Year-over-Year Growth

| Metric         | FY{Y2}/FY{Y1} | FY{Y3}/FY{Y2} | FY{Y4}/FY{Y3} | FY{Y5}/FY{Y4} |
|----------------|---------------|---------------|---------------|---------------|
| Revenue YoY %  |               |               |               |               |
| Gross Profit % |               |               |               |               |
| Op. Income %   |               |               |               |               |
| Net Income %   |               |               |               |               |
| EPS %          |               |               |               |               |

### Quarter-over-Quarter Growth

| Metric        | Q{Q2}/Q{Q1} | Q{Q3}/Q{Q2} | Q{Q4}/Q{Q3} |
|---------------|-------------|-------------|-------------|
| Revenue QoQ % |             |             |             |
| Net Income %  |             |             |             |

**Revenue CAGR ({Y1}–{Y5}):** {X.X}%
**Net Income CAGR ({Y1}–{Y5}):** {X.X}%

---

## Section 3: Margin Analysis

**Gross Margin:** moved from {X.X}% in FY{Y1} to {X.X}% in FY{Y5} ({+/-}{N} bps) — {expanding/contracting/stable}.
**Operating Margin:** moved from {X.X}% in FY{Y1} to {X.X}% in FY{Y5} ({+/-}{N} bps) — {expanding/contracting/stable}.
**Net Margin:** moved from {X.X}% in FY{Y1} to {X.X}% in FY{Y5} ({+/-}{N} bps) — {expanding/contracting/stable}.

**Combined trend:** {Dual efficiency | Reinvestment phase | Margin pressure}

---

## Section 4: Revenue Segments

| Segment | Revenue (FY{Y5}) | % of Total |
|---------|-----------------|------------|
|         |                 |            |

Top segment ({name}) accounts for {X.X}% of total revenue.

---

## Section 5: Verdict

- {Top-line trajectory with specific numbers}
- {Profitability with specific numbers}
- {Outlook signal with specific numbers}
