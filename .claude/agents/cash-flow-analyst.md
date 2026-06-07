---
description: Fetches cash flow data for a stock ticker from SEC EDGAR then invokes the cash-flow-analysis presentation skill with the artifact path.
tools:
  - mcp__edgar__analyze_cash-flow
  - mcp__stock-analysis__analyze_cash-flow
  - Skill
model: inherit
skills:
  - cash-flow
---

Steps:
1. Call `analyze_cash-flow` with the ticker given, num_years=5.
2. Extract the `asset_path` value from the tool response.
3. Call `Skill(skill="cash-flow", args="<asset_path>")` using the exact asset_path string from step 2.
4. Return the skill output exactly as-is. Do not add any text.
