---
name: cash-flow
description: Presentation skill — cash flow. Receives artifact asset_path in {args}, reads JSON, renders structured report template.
tools:
  - Bash
  - Read
---

Read the artifact at `{args}` using the Read tool, then fill every cell in the template below with real data from that file. Output only the completed template — no preamble, no commentary, no extra sections.

Rules: $B (1dp) if ≥$1B, else $M. Percentages 1dp. N/R for null. No emoji.

---

# {COMPANY_NAME} ({TICKER}) — Cash Flow Analysis
**Source:** SEC EDGAR 10-K XBRL filings
**Coverage:** {N} fiscal years

---

## Section 1: Cash Flow Statement Table

| Metric                      | FY{Y1} | FY{Y2} | FY{Y3} | FY{Y4} | FY{Y5} |
|-----------------------------|--------|--------|--------|--------|--------|
| **Operating Cash Flow**     |        |        |        |        |        |
| Depreciation & Amort.       |        |        |        |        |        |
| Stock-Based Compensation    |        |        |        |        |        |
| **Investing Cash Flow**     |        |        |        |        |        |
| Capital Expenditures        |        |        |        |        |        |
| Acquisitions                |        |        |        |        |        |
| **Financing Cash Flow**     |        |        |        |        |        |
| Dividends Paid              |        |        |        |        |        |
| Share Buybacks              |        |        |        |        |        |
| Debt Issued                 |        |        |        |        |        |
| Debt Repaid                 |        |        |        |        |        |

---

## Section 2: Free Cash Flow & Efficiency

| Metric                  | FY{Y1} | FY{Y2} | FY{Y3} | FY{Y4} | FY{Y5} |
|-------------------------|--------|--------|--------|--------|--------|
| **Free Cash Flow**      |        |        |        |        |        |
| **FCF Margin %**        |        |        |        |        |        |
| CapEx / Revenue %       |        |        |        |        |        |
| **Shareholder Return**  |        |        |        |        |        |

---

## Section 3: Cash Generation Quality

{Three sentences: OCF to FCF conversion, FCF trajectory, capital intensity.}

---

## Section 4: Capital Allocation (FY{Y5})

FCF available: {$X.XB}

| Allocation      | {FY{Y5}} | % of FCF |
|-----------------|----------|----------|
| Share Buybacks  |          |          |
| Dividends       |          |          |
| Debt Repayment  |          |          |
| Total Returned  |          |          |

---

## Section 5: Debt Activity

{Three sentences: debt issued, debt repaid, net debt change. Plus full-period cumulative summary.}

---

## Section 6: Verdict

- {Cash generation with specific numbers}
- {Capital intensity with specific numbers}
- {Shareholder returns with specific numbers}
