---
name: balance-sheet
description: Presentation skill — balance sheet. Receives artifact asset_path in {args}, reads JSON, renders structured report template.
tools:
  - Bash
  - Read
---

Read the artifact at `{args}` using the Read tool, then fill every cell in the template below with real data from that file. Output only the completed template — no preamble, no commentary, no extra sections.

Rules: $B (1dp) if ≥$1B, else $M. Ratios 2dp. Per-share 2dp. N/R for null. No emoji.

---

# {COMPANY_NAME} ({TICKER}) — Balance Sheet Analysis
**Source:** SEC EDGAR 10-K XBRL filings
**Coverage:** {N} fiscal years

---

## Section 1: Financial Position Table

| Metric                   | FY{Y1} | FY{Y2} | FY{Y3} | FY{Y4} | FY{Y5} |
|--------------------------|--------|--------|--------|--------|--------|
| **Total Assets**         |        |        |        |        |        |
| Current Assets           |        |        |        |        |        |
| Cash & Equivalents       |        |        |        |        |        |
| Marketable Securities    |        |        |        |        |        |
| Accounts Receivable      |        |        |        |        |        |
| Inventory                |        |        |        |        |        |
| PP&E (Net)               |        |        |        |        |        |
| Goodwill                 |        |        |        |        |        |
| **Total Liabilities**    |        |        |        |        |        |
| Current Liabilities      |        |        |        |        |        |
| Long-Term Debt           |        |        |        |        |        |
| Total Debt               |        |        |        |        |        |
| **Stockholders' Equity** |        |        |        |        |        |
| Retained Earnings        |        |        |        |        |        |

---

## Section 2: Capital Structure & Key Ratios

| Metric             | FY{Y1} | FY{Y2} | FY{Y3} | FY{Y4} | FY{Y5} |
|--------------------|--------|--------|--------|--------|--------|
| Working Capital    |        |        |        |        |        |
| Net Cash Position  |        |        |        |        |        |
| Debt / Equity      |        |        |        |        |        |
| Debt / Assets      |        |        |        |        |        |
| Current Ratio      |        |        |        |        |        |
| Book Value / Share |        |        |        |        |        |

---

## Section 3: Liquidity Analysis

{Three sentences: Current Ratio trend, Working Capital trend, Net Cash Position trend.}

---

## Section 4: Debt Profile

{Three sentences: total debt quantum, debt trajectory, leverage assessment.}

---

## Section 5: Equity & Book Value

{Three sentences: stockholders' equity trend, retained earnings, book value per share trend.}

---

## Section 6: Verdict

- {Asset base with specific numbers}
- {Leverage position with specific numbers}
- {Liquidity with specific numbers}
