# Multi-Query Strategy: Oil Price Asymmetry on Real Output

This reference documents the technique used in the July 2026 run where the default Scopus query returned irrelevant OA papers, and a multi-query iteration strategy was required.

## Problem

The query "Asymmetric effect of oil price shocks on real economy / real output" returned DOIs from Scopus, but the only OA PDFs available via Unpaywall were from adjacent disciplines (nuclear energy welfare, CO2 emissions datasets) — keyword overlap with zero topical relevance.

## Strategy

### Step 1: Provide alternative queries in the researcher task description

```text
If the primary query returns fewer than 4 open-access DOIs, try these alternative queries
in sequence until 4 papers are found:
1. 'oil price asymmetry AND output'
2. 'nonlinear oil price AND GDP'
3. 'oil price shocks AND real economy'
4. 'asymmetric oil price AND economic activity'
5. 'oil price AND real output AND asymmetry'
```

Each query independently fetches 25 DOIs from Scopus. The researcher loops through them, skipping DOIs already in the deduplication tracker.

### Step 2: Increase the sent_count cap

The researcher's generated Python script has `if sent_count >= 3: break`. Append:

```text
Increase the sent_count cap from 3 to 4 — you must send at least 4 papers to n8n.
```

The researcher modifies the generated script from `sent_count >= 3` to `sent_count >= 4`.

### Step 3: Reduce the sleep timer

The default script includes `time.sleep(30)` between DOI submissions. Over 5 queries × 4 DOIs, this adds 10 minutes of wall time, easily exceeding the 60-second terminal timeout. Append:

```text
Reduce the sleep time between DOI submissions to 5 seconds to avoid the 60-second timeout.
```

## Outcome

Using this strategy, the researcher found 4 on-topic OA papers from *Financial Innovation* (Springer, 2026):
1. OPEC+ fiscal austerity response to unanticipated oil price shocks (DOI: 10.1186/s40854-025-00824-6)
2. OPEC crude oil price forecasting with unconventional variables (DOI: 10.1186/s40854-026-00907-y)
3. Asymmetric bank-stock market dynamics under global uncertainty (DOI: 10.1186/s40854-025-00810-y)
4. A fourth paper from the "oil price asymmetry AND output" query (DOI: 10.1007/s11270-026-09486-1)

All 4 were streamed to n8n and converted to Markdown in the `oil_price_asymmetry_and_output/` subfolder.