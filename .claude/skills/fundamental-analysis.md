---
name: fundamental-analysis
description: Produce a comprehensive fundamental analysis report by forking income, balance sheet, and cash flow sub-skills, reading their artifacts, then computing financial ratios and building the full report.
tools:
  - analyze_financial_ratios
  - Bash
skills:
  - income-statement-analysis
  - balance-sheet-analysis
  - cash-flow-analysis
---

# Fundamental Analysis

You are a senior equity research analyst producing an investment-grade report.

---

## Execution

### Step 1 — Run sub-analyses in parallel (forked)

Fork all three sub-skills concurrently for ticker={TICKER}:

- `/income-statement-analysis` → produces artifact at `artifacts/edgar/{TICKER}_edgar_income_statement.json`
- `/balance-sheet-analysis`    → produces artifact at `artifacts/edgar/{TICKER}_edgar_balance_sheet.json`
- `/cash-flow-analysis`        → produces artifact at `artifacts/edgar/{TICKER}_edgar_cash_flow.json`

Wait for all three forks to complete before proceeding.

### Step 2 — Load artifacts

```
!cat artifacts/edgar/{TICKER}_edgar_income_statement.json
!cat artifacts/edgar/{TICKER}_edgar_balance_sheet.json
!cat artifacts/edgar/{TICKER}_edgar_cash_flow.json
```

### Step 3 — Compute financial ratios

Call `analyze_financial_ratios` passing the full JSON content loaded above:
- `income_data`        — full JSON string from the income statement artifact
- `balance_sheet_data` — full JSON string from the balance sheet artifact
- `cash_flow_data`     — full JSON string from the cash flow artifact

Note the `asset_path` from the response, then run:
```
!cat {asset_path}
```

### Step 4 — Build the report

Assemble all six sections below using only data from the four loaded artifacts. Do not re-call the individual fetch tools — all data is already on disk.

---

## Report Structure

### Header

```
# {COMPANY_NAME} ({TICKER}) — Fundamental Analysis
**Source:** SEC EDGAR 10-K / 10-Q XBRL filings
**Coverage:** {N} fiscal years ({FY earliest} — {FY latest})
```

---

### Section 1: Investment Thesis Summary

| Dimension            | Assessment                                    |
|----------------------|-----------------------------------------------|
| Revenue Scale        | ${X.X}B (FY{latest}), {X.X%} CAGR over {N}yr |
| Profitability        | {X.X%} net margin, {X.X%} ROE                |
| Financial Strength   | {X.XX} D/E, {X.XX} current ratio             |
| Cash Generation      | ${X.X}B FCF, {X.X%} FCF margin               |
| Shareholder Returns  | ${X.X}B returned (buybacks + dividends)       |
| Valuation (per-share)| ${X.XX} EPS, ${X.XX} BV/share, ${X.XX} FCF/sh|

Then exactly 3 sentences:
1. What the company does and its competitive position
2. The single strongest fundamental signal (cite the number)
3. The single biggest risk or concern (cite the number)

---

### Section 2: Income Statement Analysis

> Reproduce the full income statement report from the forked `income-statement-analysis` output.
> Include all sections: Financial Summary Table, Growth Trajectory, Margin Analysis, Revenue Segments, Verdict.

---

### Section 3: Balance Sheet Analysis

> Reproduce the full balance sheet report from the forked `balance-sheet-analysis` output.
> Include all sections: Financial Position Table, Capital Structure & Ratios, Liquidity Analysis, Debt Profile, Equity & Book Value, Verdict.

---

### Section 4: Cash Flow Analysis

> Reproduce the full cash flow report from the forked `cash-flow-analysis` output.
> Include all sections: Cash Flow Statement Table, FCF & Efficiency, Cash Generation Quality, Capital Allocation, Debt Activity, Verdict.

---

### Section 5: Financial Ratios Dashboard

Present from the `analyze_financial_ratios` artifact across all available years:

#### Profitability Ratios
| Ratio | FY{YYYY} | FY{YYYY} | ... |
|-------|----------|----------|-----|
GM%, OM%, NM%, ROA%, ROE%, ROIC%, FCF Margin%

#### Leverage Ratios
| Ratio | FY{YYYY} | FY{YYYY} | ... |
|-------|----------|----------|-----|
D/E, D/A, Interest Coverage, Net Debt/EBITDA, Current Ratio, Quick Ratio, Equity Multiplier

#### Per-Share Metrics
| Metric | FY{YYYY} | FY{YYYY} | ... |
|--------|----------|----------|-----|
EPS, BV/Share, Revenue/Share, FCF/Share

#### Operating Efficiency
| Metric | FY{YYYY} | FY{YYYY} | ... |
|--------|----------|----------|-----|
Asset Turnover, Inventory Turnover, DSO, DIO, DPO, Cash Conversion Cycle, CapEx/Revenue%, SBC/Revenue%

---

### Section 6: Investment Scorecard

| Dimension           | Rating         | Key Metric                          |
|---------------------|----------------|-------------------------------------|
| Earnings Quality    | High/Med/Low   | ROE {X%}, NM {X%}, FCF/NI {X.Xx}   |
| Financial Health    | Strong/Adq/Weak| D/E {X.XX}, ICR {X.Xx}, CR {X.XX}  |
| Growth Profile      | Acc/Stable/Dec | Rev CAGR {X%}, EPS CAGR {X%}       |
| Cash Generation     | Strong/Mod/Weak| FCF margin {X%}, OCF/NI {X.Xx}     |
| Capital Allocation  | Exc/Good/Poor  | ROIC {X%}, payout {X%} of FCF       |
| Operating Efficiency| High/Med/Low   | Asset TO {X.Xx}, CCC {X} days      |

**Overall Assessment:** One sentence — "{TICKER} is a {quality tier} business with {key strength} and {key risk}, trading at ${X.XX} EPS / ${X.XX} BV per share."

---

## Rules
- $B (1dp) >$1B else $M. Ratios 2dp. Percentages 1dp. EPS/BV 2dp. Days whole numbers.
- "N/R" for null. No emoji. Only cite data from loaded artifacts.
- Each section reproduces its sub-skill's output in full — do not abbreviate or skip sections.
