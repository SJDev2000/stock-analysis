---
name: sentiment-analysis
description: Multi-source sentiment analysis. Receives ticker in {args}. Runs reddit-analyst and stocktwits-analyst agents in parallel, then assembles the combined report.
tools:
  - Agent
---

Produce the complete sentiment analysis for {args}.

## Step 1 — Run both agents in parallel

Invoke these simultaneously (pass the ticker {args} in each prompt):

1. `Agent(subagent_type="reddit-analyst", prompt="Run Reddit sentiment analysis for {args}.")`
2. `Agent(subagent_type="stocktwits-analyst", prompt="Run Stocktwits sentiment analysis for {args}.")`

Wait for both to complete. Each returns a structured JSON block.

## Step 2 — Compute composite score

From the two JSON blocks:

**Composite FSS** = (Reddit_FSS × 0.6) + (Stocktwits_FSS × 0.4)
If one source is unavailable, use the available source at weight 1.0.

**FSS label:** >+1.2 Strongly Bullish | +0.6–+1.2 Bullish | +0.2–+0.6 Mildly Bullish | -0.2–+0.2 Neutral | -0.6– -0.2 Mildly Bearish | -1.2– -0.6 Bearish | <-1.2 Strongly Bearish. Override to Mixed if bull/bear weight units within 15%.

## Step 3 — Assemble and output the report

Fill in the report template below using data from both agent outputs. Output only the completed report — no preamble, no commentary.

---

# {TICKER} ({COMPANY_NAME}) — Multi-Source Sentiment Report
**Sources:** Reddit RSS (public feeds) | Stocktwits Public API
**Coverage:** week window (Reddit) | Latest 30 messages (Stocktwits)
**Reddit Sample:** {posts_fetched} posts fetched → {filtered_in} relevant → {filtered_out} excluded → {total_comments} comments analyzed
**Stocktwits Sample:** {message_count} messages | {labeled_bullish} Bullish / {labeled_bearish} Bearish labeled | {unlabeled_count} unlabeled (inferred)

---

### Section 1: Composite Sentiment Verdict

| Dimension | Composite | Reddit | Stocktwits |
|-----------|-----------|--------|------------|
| Overall Sentiment Label | | | |
| Final Sentiment Score (FSS) | | | |
| Aggregate Weighted Score (AWS) | N/A | | |
| Confidence | | | |
| Bull Weight Units | N/A | | |
| Bear Weight Units | N/A | | |
| Bull/Bear Ratio | N/A | | |
| Source Weight | — | 60% | 40% |

{3 sentences: dominant crowd narrative, strongest bullish signal with source, strongest bearish signal with source.}

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

---

### Section 4: Coverage Metrics

| Metric | Reddit | Stocktwits |
|--------|--------|------------|
| Items fetched | | |
| Items analyzed | | |
| Exclusion rate | | N/A |
| Sample depth | week window | Latest 30 (real-time) |
| Unique sources | | Stocktwits stream |
| Most active source | | N/A |

---

### Section 5: Subreddit Breakdown (Reddit)

| Subreddit | Relevant Posts | Dominant Sentiment | Avg Score |
|-----------|----------------|--------------------|-----------|

---

### Section 6: Key Themes — Cross-Platform

{Up to 8 themes, each tagged [Reddit | Stocktwits | Both]:}

**{Theme Name}** [{source}]
Sentiment: {label} | Mentions: {N}
{One sentence.}
> "{Exact quote ≤35 words, attributed to r/subreddit or @username}"

---

### Section 7: Notable Posts & Messages

**Top 3 Reddit Posts** (highest absolute weighted score):

```
[{SENTIMENT}] r/{subreddit} — "{title}"
Weighted Score: {±X.X} | Comments: {N}
Excerpt: "{≤40 words}"
```

**Top 3 Stocktwits Messages** (highest absolute weighted score):

```
[{SENTIMENT}] @{username}
Weighted Score: {±X.X} | Label: {Bullish|Bearish|Unlabeled}
Message: "{≤40 words}"
```

---

### Section 8: Bull vs Bear Case — Combined

**Bull Case** (from Reddit + Stocktwits crowd)
- {Up to 5 bullets citing specific claims and sources}

**Bear Case** (from Reddit + Stocktwits crowd)
- {Up to 5 bullets citing specific claims and sources}

---

### Section 9: Cross-Platform Divergence

| Dimension | Reddit Signal | Stocktwits Signal | Divergence? |
|-----------|--------------|-------------------|-------------|
| FSS | | | Yes/No |
| Dominant sentiment | | | Yes/No |
| Top theme | | | Yes/No |

{1–2 sentences interpreting divergence or convergence.}

---

### Section 10: Trading Signal

```
COMPOSITE SIGNAL:  {BULLISH / BEARISH / NEUTRAL / MIXED / CONTRARIAN}
SIGNAL STRENGTH:   {STRONG / MODERATE / WEAK}
CONFIDENCE:        {HIGH / MODERATE / LOW}
REDDIT SIGNAL:     {label} (FSS {±X.XX})
STOCKTWITS SIGNAL: {label} (FSS {±X.XX})
```

{2 sentences: near-term implication, consensus vs divergence assessment.}

Risk flags — mark all that apply:
- [ ] Composite FSS > +1.5 — crowded bullish, elevated contrarian risk
- [ ] Composite FSS < -1.5 — potential capitulation or short-squeeze setup
- [ ] LOW confidence — insufficient sample on one or both sources
- [ ] Reddit/Stocktwits divergence >0.8 FSS points — conflicting crowd signals
- [ ] High exclusion rate (>60%) on Reddit — low signal quality
- [ ] Single subreddit >70% of Reddit signal — narrow sample bias
- [ ] Stocktwits <10 messages — real-time sample too thin

---

Rules: Scores 2dp. Percentages 1dp. N/R for unavailable data. N/A for non-applicable. No emoji. Every table fully populated.
