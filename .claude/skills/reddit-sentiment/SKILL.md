---
name: reddit-sentiment
description: Presentation skill — Reddit sentiment. Receives artifact asset_path in {args}, reads JSON, scores all posts and comments, outputs structured JSON result for the parent sentiment-analysis skill.
tools:
  - Bash
  - Read
---

Read the Reddit artifact at `{args}` using the Read tool. Score every post and comment using the rules below. Output ONLY the JSON block — no prose, no markdown outside the fence.

## Scoring Rules

**Scale:** Strongly Bullish +2 | Bullish +1 | Mildly Bullish +0.5 | Neutral 0 | Mixed 0 | Mildly Bearish -0.5 | Bearish -1 | Strongly Bearish -2

**Content weight:** post 3×, top-level comment ≥50 words 2×, top-level comment <50 words 1×, reply 0.5×

**Subreddit multiplier:** r/wallstreetbets, r/investing, r/ValueInvesting, r/stocks, r/StockMarket 1.0× | other finance 0.8× | non-finance 0.5×

**Per-item score** = raw × content_weight × subreddit_multiplier

**AWS** = Σ(weighted scores) / Σ(weights)

**FSS** = AWS × confidence modifier: <5 posts → 0.5×, 5–15 → 0.8×, >15 → 1.0×

**FSS label:** >+1.2 Strongly Bullish | +0.6–+1.2 Bullish | +0.2–+0.6 Mildly Bullish | -0.2–+0.2 Neutral | -0.6– -0.2 Mildly Bearish | -1.2– -0.6 Bearish | <-1.2 Strongly Bearish. Override to Mixed if bull weight units within 15% of bear weight units.

## Output

```json
{
  "source": "Reddit",
  "ticker": "",
  "time_filter": "",
  "posts_fetched": 0,
  "filtered_in": 0,
  "filtered_out": 0,
  "total_comments": 0,
  "unique_subreddits": 0,
  "aws": 0.00,
  "fss": 0.00,
  "fss_label": "",
  "confidence": "LOW|MODERATE|HIGH",
  "bull_weight_units": 0.00,
  "bear_weight_units": 0.00,
  "bull_bear_ratio": 0.0,
  "signal_distribution": {
    "Strongly Bullish": {"posts": 0, "comments": 0, "weight_adj_units": 0.00},
    "Bullish":          {"posts": 0, "comments": 0, "weight_adj_units": 0.00},
    "Mildly Bullish":   {"posts": 0, "comments": 0, "weight_adj_units": 0.00},
    "Neutral":          {"posts": 0, "comments": 0, "weight_adj_units": 0.00},
    "Mixed":            {"posts": 0, "comments": 0, "weight_adj_units": 0.00},
    "Mildly Bearish":   {"posts": 0, "comments": 0, "weight_adj_units": 0.00},
    "Bearish":          {"posts": 0, "comments": 0, "weight_adj_units": 0.00},
    "Strongly Bearish": {"posts": 0, "comments": 0, "weight_adj_units": 0.00}
  },
  "subreddit_breakdown": [
    {"subreddit": "", "relevant_posts": 0, "dominant_sentiment": "", "avg_score": 0.00}
  ],
  "top_themes": [],
  "notable_posts": [
    {
      "subreddit": "",
      "title": "",
      "sentiment_label": "",
      "weighted_score": 0.0,
      "comment_count": 0,
      "excerpt": ""
    }
  ],
  "asset_path": ""
}
```

Populate every field. `notable_posts` = top 3 by absolute weighted score. `top_themes` = up to 4 recurring topic strings.
