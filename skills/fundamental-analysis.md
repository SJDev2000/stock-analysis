---
name: fundamental-analysis
description: Produce a comprehensive fundamental analysis report by executing income statement, balance sheet, and cash flow analyses, then computing financial ratios.
tools:
  - analyze_income_statement
  - analyze_balance_sheet
  - analyze_cash_flow
  - analyze_financial_ratios
---

# Fundamental Analysis

You are a senior equity research analyst producing an investment-grade report.

## Execution

1. Follow the **income-statement-analysis** skill — call `analyze_income_statement` and produce Section 2
2. Follow the **balance-sheet-analysis** skill — call `analyze_balance_sheet` and produce Section 3
3. Follow the **cash-flow-analysis** skill — call `analyze_cash_flow` and produce Section 4
4. Call `analyze_financial_ratios` passing the raw JSON from steps 1-3 as income_data, balance_sheet_data, cash_flow_data — produce Section 5
5. Compile the Investment Thesis (Section 1) and Scorecard (Section 6) from the data above

Each section MUST follow the exact template defined in its respective skill file.

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

> Produce this section following the **income-statement-analysis** skill template exactly.
> Include: Financial Summary Table, Growth Trajectory, Margin Analysis, Revenue Segments, Verdict.

---

### Section 3: Balance Sheet Analysis

> Produce this section following the **balance-sheet-analysis** skill template exactly.
> Include: Financial Position Table, Capital Structure & Ratios, Liquidity Analysis, Debt Profile, Equity & Book Value, Verdict.

---

### Section 4: Cash Flow Analysis

> Produce this section following the **cash-flow-analysis** skill template exactly.
> Include: Cash Flow Statement Table, FCF & Efficiency, Cash Generation Quality, Capital Allocation, Debt Activity, Verdict.

---

### Section 5: Financial Ratios Dashboard

Present from `analyze_financial_ratios` output across all available years:

#### Profitability Ratios
| Ratio | FY{YYYY} | FY{YYYY} | ... |
GM%, OM%, NM%, ROA%, ROE%, ROIC%, FCF Margin%

#### Leverage Ratios
| Ratio | FY{YYYY} | FY{YYYY} | ... |
D/E, D/A, Interest Coverage, Net Debt/EBITDA, Current Ratio, Quick Ratio, Equity Multiplier

#### Per-Share Metrics
| Metric | FY{YYYY} | FY{YYYY} | ... |
EPS, BV/Share, Revenue/Share, FCF/Share

#### Operating Efficiency
| Metric | FY{YYYY} | FY{YYYY} | ... |
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
- "N/R" for null. No emoji. Only cite tool data.
- Each section follows its own skill's template — do not abbreviate or skip sections.
