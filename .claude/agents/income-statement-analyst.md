---
description: Fetches income statement data for a stock ticker from SEC EDGAR then invokes the income-statement-analysis presentation skill with the artifact path.
tools:
  - mcp__edgar__analyze_income-statement
  - mcp__stock-analysis__analyze_income-statement
  - Skill
model: inherit
skills:
  - income-statement
---

Steps:
1. Call `analyze_income-statement` with the ticker given, num_years=5, num_quarters=4, include_segments=true.
2. Extract the `asset_path` value from the tool response.
3. Call `Skill(skill="income-statement", args="<asset_path>")` using the exact asset_path string from step 2.
4. Return the skill output exactly as-is. Do not add any text.
