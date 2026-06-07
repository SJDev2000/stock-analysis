---
name: fundamental-analysis
description: Full investment-grade fundamental analysis. Receives ticker in {args}. Runs income, balance sheet, and cash flow agents in parallel, computes ratios, then assembles the complete report.
tools:
  - mcp__stock-analysis__analyze_financial_ratios
  - mcp__edgar__analyze_financial_ratios
  - Agent
---

Produce the complete fundamental analysis for {args}.

## Step 1 — Run all three agents in parallel

Invoke these simultaneously (pass the ticker {args} in each prompt):

1. `Agent(subagent_type="income-statement-analyst", prompt="Run income statement analysis for {args}.")`
2. `Agent(subagent_type="balance-sheet-analyst", prompt="Run balance sheet analysis for {args}.")`
3. `Agent(subagent_type="cash-flow-analyst", prompt="Run cash flow analysis for {args}.")`

Wait for all three to complete. Each returns a fully formatted report section.

## Step 2 — Compute ratios

Call `analyze_financial_ratios(ticker="{args}")`.

## Step 3 — Assemble and output

Output the three agent reports concatenated in order, then the ratios section below. Separate each with `---`. Do not add any other text, preamble, or commentary.

{income_statement_agent_output}

---

{balance_sheet_agent_output}

---

{cash_flow_agent_output}

---

## Section 5: Financial Ratios Dashboard

{ratios_tool_output}
