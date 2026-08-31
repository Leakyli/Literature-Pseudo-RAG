# Diagnosing Zero-DOI Researcher Output

## Problem

The kanban-spawned researcher worker runs a Python script that queries Scopus → Unpaywall → n8n. When the worker finishes and says "all DOIs were already processed or lacked OA PDFs," the kanban log only shows the agent's conversation summary — **not the script's stdout**. You see the final conclusion but not the per-DOI trace.

## Failure Modes to Distinguish

| Mode | Symptom | Diagnosis |
|------|---------|-----------|
| (A) Scopus returned 0 results | `processed_dois.txt` doesn't exist. Manual Scopus query returns 0 entries. | Query too narrow |
| (B) Scopus returned DOIs but Unpaywall found no OA PDFs | `processed_dois.txt` doesn't exist (no DOI ever reached the "success" branch of the script). Manual Scopus query returns DOIs. | Topic may not have OA versions; try older papers |
| (C) Script crashed silently | `processed_dois.txt` doesn't exist. Manual Scopus query may or may not work. No error visible in kanban log. | API key issue, rate limit, network timeout |

## Diagnosis Steps

### 1. Check the tracker file

```bash
cat ~/.hermes/processed_dois.txt 2>/dev/null
```

- **File exists with DOIs:** Those were the ones that resolved to OA URLs and were sent to n8n in previous runs. The current run's fresh DOIs failed at Unpaywall.
- **File doesn't exist:** No DOI has ever been successfully resolved — either Scopus returned nothing or Unpaywall returned no OA URLs for anything.

### 2. Run a manual Scopus query

```bash
python3 -c "
import os, urllib.parse, urllib.request, json
query = '<EXACT_QUERY_USED>'
url = 'https://api.elsevier.com/content/search/scopus?query=' + urllib.parse.quote(query) + '&field=prism:doi,dc:title&count=25'
req = urllib.request.Request(url, headers={'X-ELS-APIKey': os.environ.get('ELSEVIER_API_KEY',''), 'Accept': 'application/json'})
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode())
entries = data.get('search-results', {}).get('entry', [])
print(f'Total: {len(entries)}')
for e in entries:
    print(f\"  {e.get('prism:doi','N/A')} — {e.get('dc:title','N/A')[:80]}\")
"
```

- **0 entries →** widen the query. Drop niche abbreviations (e.g. "XAI" → "Explainable AI"), add broader synonyms, and target older years explicitly.
- **Entries found →** the Unpaywall resolution is the bottleneck. Resume the researcher's session to inspect Unpaywall responses directly.

### 3. Resume the researcher session

The kanban log shows a resume command at the end:

```
hermes --resume <session_hash> -p researcher
```

Run this to access the researcher's full conversation, including the actual stdout from the heredoc Python script. This lets you see per-DOI Unpaywall errors and response statuses.

## Why This Happens

The kanban agent wraps the Python script in a heredoc and passes it to `terminal()`. The script's stdout is printed to the terminal during execution but is **not captured into the kanban log conversation** — the kanban log is the agent's own chat transcript, not the terminal output. The agent then summarizes the outcome ("all DOIs already processed or no OA PDF"), which is all that shows in the log.

To see the raw script output, you must either:
- Resume the researcher session (`hermes --resume ...`)
- Or run the Scopus query manually (step 2 above)