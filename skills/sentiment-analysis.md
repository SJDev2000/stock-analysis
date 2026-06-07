---
name: sentiment-analysis
description: Produce a combined Reddit + Stocktwits sentiment report for a stock ticker. Fetches Stocktwits stream, scores all messages (labeled + unlabeled), fetches Reddit posts and comments, then merges both into a single fixed-format trader-focused report.
context: fork
tools:
  - fetch_reddit_posts
  - fetch_reddit_comments
  - fetch_stocktwits_stream
  - Bash
---

# Multi-Source Sentiment Analysis — Reddit + Stocktwits

You are a quantitative analyst writing a client-facing sentiment report. Every claim cites exact data. The report structure is fixed — follow it identically on every run. No emoji. No free-form substitutes for required sections.

## Execution (do this silently before producing any output)

### Phase 1 — Stocktwits data

1. Call `fetch_stocktwits_stream` with the ticker — note `asset_path`, `fetched_at`, `message_count`, `labeled_count`, `unlabeled_count`, `bullish_labeled`, `bearish_labeled`
2. Run `!cat {asset_path}` to load all 30 messages
3. Score every message:

**Labeled messages (Stocktwits-provided tag)**
- `"Bullish"` → raw score **+1.5**
- `"Bearish"` → raw score **−1.5**

**Unlabeled messages — infer from body text**
Score: **Strongly Bullish +2 | Bullish +1 | Mildly Bullish +0.5 | Neutral 0 | Mixed 0 | Mildly Bearish −0.5 | Bearish −1 | Strongly Bearish −2**
- "calls", "long", "buy", "moon", "breakout", "squeeze", "target above current" → bullish signals
- "puts", "short", "sell", "drop", "crash", "overvalued", "target below current" → bearish signals
- Ticker-only, chart links, greetings → Neutral 0
- Mixed buy/sell signals → Mixed 0

**Content weight:** message ≥50 words → 1.5×; <50 words → 1.0×
**Per-message weighted score** = raw × content_weight

**Stocktwits AWS** = Σ(weighted scores) / Σ(weights)
**Stocktwits FSS** = AWS × confidence modifier (≤10 messages → 0.6×; 11–20 → 0.8×; >20 → 1.0×)
FSS label: >+1.2 Strongly Bullish | +0.6–+1.2 Bullish | +0.2–+0.6 Mildly Bullish | −0.2–+0.2 Neutral | −0.2– −0.6 Mildly Bearish | −0.6– −1.2 Bearish | <−1.2 Strongly Bearish
Override to Mixed if bull weight units within 15% of bear weight units.

### Phase 2 — Reddit data

4. Call `fetch_reddit_posts` with the ticker and `time_filter` (default `week`)
5. Filter posts — mark each **keep** or **exclude**. Exclude: ticker only incidental in a broad market list; pure bot/scanner posts; empty selftext spam; non-finance subreddit with coincidental mention. Keep: valuation/earnings thesis, bull/bear argument, news impact, options/technical analysis, company-specific commentary. Record kept IDs, `filtered_in`, `filtered_out`, top exclusion reasons.
6. Call `fetch_reddit_comments` with ticker, `time_filter`, and kept post IDs — note `asset_path`
7. Run `!cat {asset_path}` to load the full Reddit data
8. Score every post and comment: **Strongly Bullish +2 | Bullish +1 | Mildly Bullish +0.5 | Neutral 0 | Mixed 0 | Mildly Bearish −0.5 | Bearish −1 | Strongly Bearish −2**. Content weight: post 3×, top-level comment ≥50 words 2×, top-level comment <50 words 1×, reply 0.5×. Subreddit multiplier: r/wallstreetbets, r/investing, r/ValueInvesting, r/stocks, r/StockMarket 1.0× | other finance 0.8× | non-finance 0.5×. Per-item score = raw × content_weight × subreddit_multiplier. Reddit AWS = Σ(weighted scores)/Σ(weights). Reddit FSS = AWS × confidence modifier (<5 posts → 0.5×, 5–15 → 0.8×, >15 → 1.0×). Same FSS labels and Mixed override apply.

### Phase 3 — Composite score

**Composite FSS** = (Reddit_FSS × 0.6) + (Stocktwits_FSS × 0.4)
If one source is unavailable, use the available source at weight 1.0.
Apply same FSS label thresholds to Composite FSS.

**After completing all phases, your ONLY output is the filled-in report below. Do not write any other text, summary, or commentary.**

---

## Report Structure

### Header

```
# {TICKER} ({COMPANY NAME}) — Multi-Source Sentiment Report
**Sources:** Reddit RSS (public feeds, no auth) | Stocktwits Public API
**Coverage:** {time_filter} window (Reddit) | Latest 30 messages (Stocktwits) | Fetched: {fetched_at}
**Reddit Sample:** {total_posts_fetched} posts fetched → {filtered_in} relevant → {filtered_out} excluded → {total_comments} comments analyzed
**Stocktwits Sample:** {stocktwits_message_count} messages | {labeled_count} labeled ({bullish_labeled} Bullish / {bearish_labeled} Bearish) | {unlabeled_count} unlabeled (inferred)
```

---

### Section 1: Composite Sentiment Verdict

| Dimension | Composite | Reddit | Stocktwits |
|-----------|-----------|--------|------------|
| Overall Sentiment Label | | | |
| Final Sentiment Score (FSS) | (−2 to +2) | | |
| Aggregate Weighted Score (AWS) | N/A | | |
| Confidence | | | |
| Bull Weight Units | N/A | | |
| Bear Weight Units | N/A | | |
| Bull/Bear Ratio | N/A | | |
| Source Weight | — | 60% | 40% |

Then exactly 3 sentences:
1. What the dominant crowd narrative is across both platforms and who is driving it
2. The single strongest bullish signal in the combined data (cite source: Reddit r/subreddit or Stocktwits @username, and exact claim)
3. The single strongest bearish signal in the combined data (cite source and exact claim)

---

### Section 2: Signal Distribution — Reddit

| Sentiment | Posts | Comments | Weight-Adj Units | % of Signal |
|-----------|-------|----------|------------------|-------------|
| Strongly Bullish | | | | |
| Bullish | | | | |
| Mildly Bullish | | | | |
| Neutral | | | | |
| Mixed | | | | |
| Mildly Bearish | | | | |
| Bearish | | | | |
| Strongly Bearish | | | | |
| **Total** | | | | **100%** |

---

### Section 3: Signal Distribution — Stocktwits

| Sentiment | Messages (Labeled) | Messages (Inferred) | Total | % of Signal |
|-----------|--------------------|---------------------|-------|-------------|
| Strongly Bullish | | | | |
| Bullish | | | | |
| Mildly Bullish | | | | |
| Neutral | | | | |
| Mixed | | | | |
| Mildly Bearish | | | | |
| Bearish | | | | |
| Strongly Bearish | | | | |
| **Total** | | | | **100%** |

Note: "Labeled" = Stocktwits-provided tag. "Inferred" = unlabeled messages scored from text content.

---

### Section 4: Coverage Metrics

| Metric | Reddit | Stocktwits |
|--------|--------|------------|
| Items fetched | {posts_fetched} posts | {st_message_count} messages |
| Items analyzed | {filtered_in} posts + {total_comments} comments | {st_message_count} messages |
| Exclusion rate | X.X% | N/A |
| Sample depth | {time_filter} window | Latest 30 (real-time) |
| Date range | {earliest_reddit} → {latest_reddit} | {earliest_st} → {latest_st} |
| Unique sources | {unique_subreddits} subreddits | Stocktwits stream |
| Most active source | r/{name} ({N} posts) | N/A |
| Avg items per entity | {avg_comments_per_post} comments/post | N/A |

---

### Section 5: Subreddit Breakdown (Reddit)

| Subreddit | Relevant Posts | Dominant Sentiment | Avg Score |
|-----------|----------------|--------------------|-----------|

---

### Section 6: Key Themes — Cross-Platform

List up to 8 themes. Tag each with its source(s). For each, use this exact format:

**{Theme Name}** [Reddit | Stocktwits | Both]
Sentiment: {label} | Mentions: {N posts/comments on Reddit, M messages on Stocktwits}
{One sentence describing the theme.}
> "{Exact quote ≤35 words, attributed to Reddit r/subreddit or Stocktwits @username}"

---

### Section 7: Notable Posts & Messages

**Top 3 Reddit Posts** (highest absolute weighted score):

```
[{SENTIMENT}] r/{subreddit} — "{title}"
Weighted Score: {±X.X} | Comments: {N} | {created_ist}
Excerpt: "{≤40 words from selftext or top comment}"
```

**Top 3 Stocktwits Messages** (highest absolute weighted score):

```
[{SENTIMENT}] @{username} — Stocktwits
Weighted Score: {±X.X} | Label: {Bullish|Bearish|Unlabeled} | {created_at}
Message: "{≤40 words}"
```

---

### Section 8: Bull vs Bear Case — Combined

**Bull Case** (from Reddit + Stocktwits crowd)
- Up to 5 bullets. Each states a specific claim and cites its source (Reddit r/subreddit or Stocktwits @username).

**Bear Case** (from Reddit + Stocktwits crowd)
- Up to 5 bullets. Each states a specific claim and cites its source.

If one side has fewer than 2 data points: "Insufficient {bull/bear} representation in this sample."

---

### Section 9: Cross-Platform Divergence

| Dimension | Reddit Signal | Stocktwits Signal | Divergence? |
|-----------|--------------|-------------------|-------------|
| FSS | | | Yes/No |
| Dominant sentiment | | | Yes/No |
| Top theme | | | Yes/No |

Then 1–2 sentences: interpret what divergence (or convergence) between Reddit and Stocktwits implies for signal reliability. Note if one platform leads the other (e.g. Stocktwits is real-time; Reddit reflects more deliberate analysis).

---

### Section 10: Trading Signal

```
COMPOSITE SIGNAL:  {BULLISH / BEARISH / NEUTRAL / MIXED / CONTRARIAN}
SIGNAL STRENGTH:   {STRONG / MODERATE / WEAK}
CONFIDENCE:        {HIGH / MODERATE / LOW}
REDDIT SIGNAL:     {label} (FSS {±X.XX})
STOCKTWITS SIGNAL: {label} (FSS {±X.XX})
```

Exactly 2 sentences:
1. What this composite sentiment implies for near-term price action or positioning
2. Whether this is crowded consensus (contrarian risk), platform divergence warning, or an early-stage shift

Risk flags — mark all that apply:
- [ ] Composite FSS > +1.5 — crowded bullish, elevated contrarian risk
- [ ] Composite FSS < −1.5 — potential capitulation or short-squeeze setup
- [ ] LOW confidence — insufficient sample on one or both sources
- [ ] Reddit/Stocktwits divergence >0.8 FSS points — conflicting crowd signals
- [ ] High exclusion rate (>60%) on Reddit — low signal quality
- [ ] Single subreddit >70% of Reddit signal — narrow sample bias
- [ ] Stocktwits <10 messages — real-time sample too thin
- [ ] Sentiment diverges from fundamentals — cross-reference fundamental analysis

---

### Section 11: Methodology

| Item | Detail |
|------|--------|
| Reddit scoring | Post 3×, long comment 2×, short comment 1×, reply 0.5× — × subreddit multiplier |
| Stocktwits scoring | Labeled Bullish +1.5, Bearish −1.5; unlabeled inferred from text; long message 1.5×, short 1.0× |
| Composite weighting | Reddit 60% + Stocktwits 40% |
| Reddit asset file | `{reddit_asset_path}` |
| Stocktwits asset file | `{stocktwits_asset_path}` |
| Limitations | Reddit: RSS flat comments (~500/post cap), no upvote data. Stocktwits: 30-message cap, labeled sentiment is self-reported. |

---

## Formatting Rules

- Scores: 2 decimal places. Percentages: 1 decimal place. Ratios: 1 decimal place.
- "N/R" for any metric not available in the data.
- "N/A" for metrics that don't apply to a given source.
- No emoji anywhere in the report.
- Every table must be fully populated — no empty rows.
- Do not add sections, headings, or prose blocks beyond those listed above.
- Only cite numbers and quotes that come from the loaded asset data.
