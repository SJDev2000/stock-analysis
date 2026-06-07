---
description: Fetches Stocktwits stream for a stock ticker then invokes the stocktwits-sentiment reporting skill with the ticker.
tools:
  - mcp__stock-analysis__fetch_stocktwits_stream
  - Skill
model: inherit
skills:
  - stocktwits-sentiment
---

Steps:
1. Call `fetch_stocktwits_stream` with the ticker given.
2. Extract the `asset_path` value from the tool response.
3. Call `Skill(skill="stocktwits-sentiment", args="<asset_path>")` using the exact asset_path string from step 2.
4. Return the skill output exactly as-is. Do not add any text.
