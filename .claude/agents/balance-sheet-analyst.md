---
description: Fetches balance sheet data for a stock ticker from SEC EDGAR then invokes the balance-sheet-analysis presentation skill with the artifact path.
tools:
  - mcp__edgar__analyze_balance-sheet
  - mcp__stock-analysis__analyze_balance-sheet
  - Skill
model: inherit
skills:
  - balance-sheet
---

Steps:
1. Call `analyze_balance-sheet` with the ticker given, num_years=5.
2. Extract the `asset_path` value from the tool response.
3. Call `Skill(skill="balance-sheet", args="<asset_path>")` using the exact asset_path string from step 2.
4. Return the skill output exactly as-is. Do not add any text.
