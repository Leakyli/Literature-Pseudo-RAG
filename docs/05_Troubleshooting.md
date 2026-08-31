---
create-date: 2026-07-05
type: documentation
status: active
tags:
  - literature-rag/system-documentation
---

# Troubleshooting

This document catalogs every issue encountered during real pipeline runs, with reproduction symptoms, root cause, and verified recovery steps.

---

## 1. Rate-Limited Model on OpenRouter

**Symptom:** Worker spawns, stays alive briefly, then dies. The log shows repeated:
```
⚠️  API call failed (attempt 1/3): RateLimitError [HTTP 429]
   Model: poolside/laguna-m.1:free
   Details: 'poolside/laguna-m.1:free is temporarily rate-limited upstream'
```

**Cause:** The researcher profile was configured with `poolside/laguna-m.1:free` — a free-tier model that OpenRouter rate-limits aggressively (especially for aarch64/ARM environments or long-running sessions).

**Fix:** Update the researcher profile to use a working model:
```yaml
# ~/.hermes/profiles/researcher/config.yaml
model:
  provider: openrouter
  default: deepseek/deepseek-v4-flash  # was poolside/laguna-m.1:free
```

**Recovery after fix:**
```bash
hermes kanban --board academic-rag reclaim t_<ID>
hermes kanban --board academic-rag dispatch
```

**Prevention:** After creating a new profile, test the model first:
```bash
hermes -p researcher chat -q "Hello, can you respond?" --accept-hooks
```

---

## 2. Worker Died Silently — No PID for Running Task

**Symptom:** `hermes kanban --board academic-rag list` shows `● t_<ID>  running` but `ps aux | grep t_<ID>` returns nothing.

**Cause:** The worker process crashed before it could update its status. Common triggers:
- Missing `ELSEVIER_API_KEY` environment variable
- Model rate-limited (see #1)
- Network timeout during API call
- Python script error (syntax, missing import)

**Diagnosis:**
```bash
hermes kanban --board academic-rag log t_<ID>
```
The log shows the conversation transcript including the crash error.

**Recovery:**
```bash
hermes kanban --board academic-rag reclaim t_<ID>
hermes kanban --board academic-rag dispatch
```

---

## 3. False Positive "Spawned: 0" on Dispatch

**Symptom:** `hermes kanban --board academic-rag dispatch` reports `Spawned: 0` but the task actually was spawned and appears as `running` on `list`.

**Cause:** A known Hermes Kanban behavior where the dispatch summary counter can report 0 even when spawning succeeds.

**Fix:** Always verify with both `list` and `ps`, never trust the dispatch summary alone:
```bash
hermes kanban --board academic-rag list
ps aux | grep t_<ID> | grep -v grep
```

---

## 4. n8n Webhook Returns 200 But Is Not Registered

**Symptom:**
```bash
curl -s -X POST -H "Content-Type: application/json" -d '{}' http://localhost:5678/webhook/fetch-paper
```
Returns HTTP 200 but the body says `"This webhook is not registered"` or `{"message":"unknown webhook"}`, not `{"message":"Workflow was started"}`.

**Cause:** n8n returns HTTP 200 for both valid and invalid webhook paths. The response body is the only reliable indicator.

**Fix:** Create the fetch-paper workflow in n8n with a Webhook node configured for POST at path `fetch-paper`.

---

## 5. Timing Race — Analyst Sees Empty Directory

**Symptom:** Analyst workspace log shows repeated `ls`/`find` calls returning empty results, task eventually gets `blocked`.

**Timeline:**
```
T+0:00 — Researcher Python script completes, marks task done
T+0:00 — Analyst spawns (auto-promoted to ready, then dispatched)
T+0:10 — Analyst finds empty directory — n8n + PyMuPDF4LLM still downloading/converting
T+0:20 — n8n deposits first Markdown file
T+1:00 — n8n deposits all Markdown files
T+1:30 — Analyst hits iteration budget, gets blocked
```

**Recovery:**
```bash
# 1. Verify files have arrived
ls -la "<vault>/Research & Syntheses/<topic>/"

# 2. Unblock (reclaim only works on running tasks)
hermes kanban --board academic-rag unblock t_<ID>

# 3. Re-dispatch
hermes kanban --board academic-rag dispatch
```

**Note:** The files will be present on retry. The timing race is resolved by the retry, not by code changes — the n8n + PyMuPDF4LLM pipeline needs time, and the retry gives it that time.

---

## 6. SYNTHESIS.md Not at Root Path

**Symptom:** Looking for SYNTHESIS.md at `<vault>/Research & Syntheses/SYNTHESIS.md` and not finding it.

**Cause:** The researcher's Python script dynamically creates a **topic-specific subfolder** (e.g., `token_optimization_and_pruning_methods_for_large_language_models/`). The analyst writes SYNTHESIS.md into that subfolder.

**Find the actual path:**
```bash
find "<vault>/Research & Syntheses/" -name "SYNTHESIS.md"
```

---

## 7. Scopus Query Returns 0 Results

**Symptom:** Researcher finishes with "didn't send any DOIs to n8n" and `processed_dois.txt` doesn't exist.

**Diagnosis:**
```bash
# Run the exact Scopus query manually
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
    print(f'  {e.get(\"prism:doi\",\"N/A\")} — {e.get(\"dc:title\",\"N/A\")[:80]}')
"
```

**Fixes by failure mode:**

| Results | Fix |
|---------|-----|
| 0 entries | Widen query — drop niche acronyms, add synonyms, use broader terms |
| Entries exist but no OA PDFs | Add `-oa` or target older papers that are more likely to be open-access |
| API error (auth, timeout) | Check `ELSEVIER_API_KEY` is set and valid |

---

## 8. Worker Won't Die with SIGTERM

**Symptom:** `kill <PID>` doesn't stop the worker.

**Cause:** Kanban-spawned workers often ignore SIGTERM. They require SIGKILL.

**Fix:**
```bash
kill -9 <PID>
# Verify
ps aux | grep t_<ID> | grep -v grep
# Exit code 1 = clean kill
```

---

## 9. `hermes kanban block` Does Not Accept `--reason`

**Symptom:** Running `hermes kanban block TASK_ID --reason "..."` fails.

**Cause:** The `block` subcommand does not support a `--reason` flag.

**Workaround:** Use `comment` to annotate why a task was blocked:
```bash
hermes kanban --board academic-rag comment t_<ID> "Blocked because: <reason>"
```

---

## 10. Task is `blocked`, Not `running` — Wrong Recovery Command

**Symptom:** Attempting `reclaim` on a blocked task fails.

**Cause:** `reclaim` only works on `running` status. Blocked tasks have a different status.

**Correct recovery:**
```bash
# For blocked tasks — use unblock
hermes kanban --board academic-rag unblock t_<ID>

# Then dispatch
hermes kanban --board academic-rag dispatch
```

## Related Documentation

- [[04_Operational_Guide]] — Operational patterns and quick-start
- [[06_Reference]] — Commands, file paths, API endpoints
- [[01_Pipeline_Components]] — Component descriptions