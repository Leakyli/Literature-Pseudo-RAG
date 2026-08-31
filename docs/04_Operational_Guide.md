---
create-date: 2026-07-05
type: documentation
status: active
tags:
  - literature-rag/system-documentation
---

# Operational Guide

## Quick Start (Full Pipeline)

Run these steps to execute a complete literature search:

### 1. Pre-flight

```bash
# Check n8n is alive
curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/health

# Verify webhook is registered (read the BODY)
curl -s -X POST -H "Content-Type: application/json" -d '{}' http://localhost:5678/webhook/fetch-paper
# → Must return: {"message":"Workflow was started"}

# Ensure vault directory exists
mkdir -p "<vault>/Research & Syntheses/"
```

### 2. Initialize Board & Archive Stale Tasks

```bash
# Create board (safe to run if it exists)
hermes kanban boards create academic-rag --name "Academic Literature RAG"

# Check for stale tasks
hermes kanban --board academic-rag list

# Archive any stale tasks (batch all IDs in one call)
hermes kanban --board academic-rag archive t_abc123 t_def456 t_ghi789
```

### 3. Create Tasks

```bash
# Researcher task
hermes kanban --board academic-rag create \
  "Query the Elsevier Scopus Search API for papers regarding: <YOUR_TOPIC>. \
   DO NOT restrict searches to a specific year. If brand-new papers lack open-access links, \
   target older foundational papers. Extract DOIs, resolve them via Unpaywall, and stream the \
   URLs directly to http://localhost:5678/webhook/fetch-paper to let n8n handle the download + conversion \
   to Markdown files inside <vault>/Research & Syntheses/." \
  --assignee researcher

# Analyst task (chained to researcher with --parent)
hermes kanban --board academic-rag create \
  "Read the processed Markdown files inside <vault>/Research & Syntheses/ \
   and compile a detailed literature matrix into SYNTHESIS.md. Write the output to \
   <vault>/Research & Syntheses/SYNTHESIS.md." \
  --assignee analyst --parent <RESEARCHER_TASK_ID>
```

### 4. Dispatch Researcher

```bash
hermes kanban --board academic-rag dispatch

# Verify it actually spawned
hermes kanban --board academic-rag list
# → Should show: ● t_<ID>  running   researcher
ps aux | grep t_<ID> | grep -v grep
# → Should show a PID
```

### 5. Wait for Researcher to Complete

The researcher takes 2–5 minutes depending on:
- Scopus API response time
- Unpaywall resolution (per DOI)
- 30-second cooldowns between papers
- n8n conversion time (1–3 min per paper)

Check periodically:
```bash
hermes kanban --board academic-rag list
```

When the researcher shows `✓ t_<ID>  done`, proceed to step 6.

### 6. Dispatch Analyst

```bash
hermes kanban --board academic-rag dispatch

# Verify it spawned
hermes kanban --board academic-rag list
ps aux | grep t_<ID> | grep -v grep
```

### 7. Wait for Analyst to Complete

The analyst takes 1–3 minutes depending on paper count. Check:
```bash
hermes kanban --board academic-rag list
```

### 8. Read the Synthesis

```bash
ls -1 "<vault>/Research & Syntheses/<topic-folder>/"
cat "<vault>/Research & Syntheses/<topic-folder>/SYNTHESIS.md"
```

---

## Recovery Patterns

### Worker Died Silently (running but no PID)

Symptom: Task shows `running` but `ps aux | grep t_ID` returns nothing.

Cause: Worker crashed before finishing (API key missing, model rate-limited, network error).

**Recovery:**
```bash
# 1. Check the log for the error
hermes kanban --board academic-rag log <TASK_ID>

# 2. Reclaim (resets from running → ready)
hermes kanban --board academic-rag reclaim <TASK_ID>

# 3. Re-dispatch
hermes kanban --board academic-rag dispatch
```

### Analyst Blocked (empty directory — n8n timing race)

Symptom: Analyst log shows repeated `ls`/`find` returning empty directories. Task is `blocked`.

Cause: Researcher completed faster than n8n + the PyMuPDF4LLM microservice could download and convert PDFs.

**Recovery:**
```bash
# 1. Verify files have arrived
ls -la "<vault>/Research & Syntheses/<topic-folder>/"

# 2. Unblock (reclaim only works on running tasks)
hermes kanban --board academic-rag unblock <TASK_ID>

# 3. Re-dispatch
hermes kanban --board academic-rag dispatch
```

### Researcher Finished with 0 DOIs Sent

Three possible root causes:

| Mode | Symptom | Fix |
|------|---------|-----|
| **A** — Scopus returned 0 results | `processed_dois.txt` doesn't exist. Run manual query → 0 entries | Widen the query (add synonyms, drop acronyms) |
| **B** — Scopus had DOIs, but no OA PDFs | `processed_dois.txt` doesn't exist. Manual query returns DOIs | Target older papers, try different keywords |
| **C** — Script crashed silently | `processed_dois.txt` doesn't exist. No error in kanban log | Check API key, network, rate limits |

**Diagnosis:**
```bash
# Check the tracker
cat ~/.hermes/processed_dois.txt 2>/dev/null

# Run a manual Scopus query
python3 -c "
import os, urllib.parse, urllib.request, json
query = '<YOUR_QUERY>'
url = 'https://api.elsevier.com/content/search/scopus?query=' + urllib.parse.quote(query) + '&field=prism:doi&count=25'
req = urllib.request.Request(url, headers={'X-ELS-APIKey': os.environ.get('ELSEVIER_API_KEY',''), 'Accept': 'application/json'})
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode())
entries = data.get('search-results', {}).get('entry', [])
print(f'Total: {len(entries)}')
for e in entries:
    print(f'  {e.get(\"prism:doi\",\"N/A\")} - {e.get(\"dc:title\",\"N/A\")[:80]}')
"
```

### Stuck in `running` with PID but No Progress

If the worker PID exists but the log hasn't changed for several minutes:

```bash
# Check worker state
hermes kanban --board academic-rag log <TASK_ID> | tail -5

# Kill the worker (SIGKILL, not SIGTERM — SIGTERM often doesn't stop kanban workers)
kill -9 <PID>

# Verify it's dead
ps aux | grep t_<TASK_ID> | grep -v grep

# Reclaim and re-dispatch
hermes kanban --board academic-rag reclaim <TASK_ID>
hermes kanban --board academic-rag dispatch
```

---

## Query Design Tips

The Scopus query is the most important variable in the pipeline. Good queries find OA papers; bad queries return nothing.

**DO:**
- Use broad keywords: `"token optimization" OR "pruning" AND "large language models"`
- Include synonyms: `"model compression" OR "efficiency"`
- Remove domain-specific abbreviations: `"LLM" → "large language models"`
- Target sub-fields: `"hallucination detection" AND "edge deployment"`

**DON'T:**
- Use only acronyms: `XAI` returns fewer results than `explainable AI`
- Over-narrow: `"token pruning" AND "MoE" AND "edge" AND "INT8"` may return 0 results
- Restrict to one year — the script automatically handles year filtering

**If a run returns 0 papers, the researcher's final log will say something like:** "All DOIs were already processed or lacked OA PDFs." This is an ambiguous message — run the manual diagnosis in mode A/B/C above to determine why.

## Related Documentation

- [[05_Troubleshooting]] — Detailed troubleshooting reference
- [[06_Reference]] — Commands, file paths, API endpoints
- [[03_Configuration]] — Profile setup, API keys
- [[02_Pipeline_Flow]] — Execution flow diagrams