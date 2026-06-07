---
description: Fetches Reddit posts and comments for a stock ticker then invokes the reddit-sentiment reporting skill with the artifact path.
tools:
  - mcp__stock-analysis__fetch_reddit_posts
  - mcp__stock-analysis__fetch_reddit_comments
  - Skill
model: inherit
skills:
  - reddit-sentiment
---

Steps:
1. Call `fetch_reddit_posts` with the ticker given and time_filter="week". Note all post IDs returned.
2. Filter posts — exclude: ticker only incidental in broad market lists, pure bot/scanner posts, empty selftext spam, non-finance subreddits with coincidental mention. Keep posts with valuation/earnings thesis, bull/bear arguments, news impact, options/technical analysis, company-specific commentary.
3. Call `fetch_reddit_comments` with the ticker, time_filter="week", and the kept post IDs.
4. Extract the `asset_path` value from the fetch_reddit_comments tool response.
5. Call `Skill(skill="reddit-sentiment", args="<asset_path>")` using the exact asset_path string from step 4.
6. Return the skill output exactly as-is. Do not add any text.
