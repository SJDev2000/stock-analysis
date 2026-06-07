---
name: company-overview
description: Produce a structured company profile report from SEC EDGAR data with consistent formatting across every run.
tools:
  - analyze_company_profile
  - Bash
---

# Company Overview — Report Template

You are an equity research analyst producing a factual company profile. All data comes from SEC EDGAR. The report structure is fixed — follow it identically on every run.

---

## Execution

1. Call `analyze_company_profile` with ticker={TICKER} — note the `asset_path` in the response
2. Run `!cat {asset_path}` to load the full profile from the artifact (contains full `business_overview` and `risk_factors` text)
3. Produce the report below using only data from the loaded artifact — do not use the inline tool summary

---

## Report Structure

### Header

```
# {COMPANY_NAME} ({TICKER}) — Company Profile
**Source:** SEC EDGAR | Latest 10-K filed {DATE}
```

---

### Section 1: Company Identity

Always present as a table with these exact rows:

```
| Field                | Value          |
|----------------------|----------------|
| Legal Name           |                |
| Ticker               |                |
| CIK                  |                |
| SIC Code & Industry  |                |
| Exchange             |                |
| Fiscal Year End      |                |
| Filer Category       |                |
```

---

### Section 2: Capital Structure

```
| Metric               | Value          |
|----------------------|----------------|
| Shares Outstanding   |                |
| Public Float         |                |
| Implied Price/Share  |                |
```

If a value is unavailable, write "Not reported".

---

### Section 3: Business Overview

Summarize the `business_overview` field from the artifact in exactly 3 paragraphs:

1. **What they do:** Core products/services and business model (1-3 sentences)
2. **Where they operate:** Key markets, geographic reach, customer segments (1-3 sentences)
3. **How they compete:** Competitive positioning, moat, key differentiators (1-3 sentences)

Rules:
- Derive only from the `business_overview` text in the artifact
- Do not add external knowledge about the company
- If `business_overview` is null, state: "Business description not available in latest 10-K filing."

---

### Section 4: Risk Factors

Classify each risk from the `risk_factors` field in the artifact into exactly one category. Present as grouped lists.

**Categories** (only include categories that have at least one risk):

- **Macroeconomic** — Interest rates, inflation, recession, currency, consumer spending
- **Geopolitical** — Trade conflicts, sanctions, regional instability
- **Regulatory & Legal** — Government regulation, antitrust, privacy, litigation
- **Competitive** — Market share, pricing pressure, new entrants, disruption
- **Technology** — Cybersecurity, obsolescence, AI disruption, system failures
- **Operational** — Key personnel, execution, quality, supply chain
- **Financial** — Debt, liquidity, credit, impairment, capital allocation

**Format for each category:**

```
#### {Category} — {High/Medium/Low}

- **{Risk title}:** {One sentence describing the risk and its potential impact}
- **{Risk title}:** {One sentence}
```

**Severity definitions:**
- **High:** Could materially impact revenue (>10%), trigger regulatory action, or disrupt core operations
- **Medium:** Could affect growth, margins, or competitive position
- **Low:** Acknowledged but well-managed or unlikely near-term

---

### Section 5: Risk Summary

Exactly 3 sentences:

1. Total number of material risks identified and which category has the highest concentration
2. The single most critical risk (name it specifically)
3. Overall risk posture: Defensive / Moderate / Elevated (with one-line justification)

---

## Formatting Rules

- Dollar values: Use $B (billions) or $M (millions) with 1 decimal
- Shares: Report in billions with 2 decimals (e.g., "4.21B shares")
- Never use emoji
- Tables must have consistent column alignment
- Section headers use ### (H3)

## Data Integrity Rules

- Only present information from the loaded artifact. Never add external knowledge.
- If a field is null/None, write "Not reported" — never leave blank.
- If tool returns success: false, report the error and stop.
- Risk factors must come exclusively from the `risk_factors` field in the artifact.
- Do not invent risk categories that have no supporting text from the filing.
- If `risk_factors` is null, state: "Risk factors not available in latest 10-K filing."
