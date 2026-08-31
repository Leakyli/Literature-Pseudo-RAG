---
create-date: 2026-07-05
type: documentation
status: active
tags:
  - literature-rag/system-documentation
---

# Pipeline Components

## 1. Orchestrator (Current Hermes Session)

The orchestrator is the **human-triggered** session that invokes the [[00_Overview|Literature RAG pipeline]]. It does NOT run as a Kanban worker — it's the session you're reading this from.

**Responsibilities:**
- Load and follow the `literature-rag` skill
- Run pre-flight verification (n8n health, webhook registration, vault directory)
- Initialize/reset the Kanban board (`academic-rag`)
- Create researcher and analyst tasks with correct dependency chaining
- Dispatch the board to spawn workers
- Verify workers spawned via `ps aux` + `hermes kanban list`
- Dispatch a second time when the researcher completes to spawn the analyst
- Handle recovery (reclaim, unblock, re-dispatch) when workers fail

**Key constraint:** The dispatcher only spawns tasks already in `ready` status when it runs. It does NOT auto-dispatch when a parent completes and promotes children to `ready`. The orchestrator must manually re-dispatch for each stage.

---

## 2. Researcher Worker

**Profile:** `researcher` — loaded from `~/.hermes/profiles/researcher/config.yaml`

**Model:** `deepseek/deepseek-v4-flash` (was `poolside/laguna-m.1:free` — see [[05_Troubleshooting#Rate-Limited Model]])

**Toolsets:** `terminal`, `kanban`, `file`

**Runtime:** Spawned by Kanban dispatcher as `hermes -p researcher chat -q work kanban task t_<ID>`

### What It Actually Does

The researcher generates and executes a **Python script** via `terminal()` heredoc. The script performs the full data pipeline:

```
Step 1: Scopus Search
→ GET https://api.elsevier.com/content/search/scopus
  ?query={user_topic}&field=prism:doi&count=25
→ Headers: X-ELS-APIKey, Accept: application/json
→ Returns up to 25 DOIs

Step 2: Deduplication
→ Reads ~/.hermes/processed_dois.txt (persistent tracker)
→ Skips any DOI already sent in prior runs

Step 3: Unpaywall Resolution (for each new DOI)
→ GET https://api.unpaywall.org/v2/{doi}?email=your-email@example.com
→ Extracts best_oa_location.url_for_pdf (OA PDF URL)
→ Falls back to oa_locations[0].url_for_pdf if best_oa missing
→ Logs DOI, title, year, and whether OA PDF was found

Step 4: n8n Streaming (for each resolved OA PDF)
→ POST to http://localhost:5678/webhook/fetch-paper
→ Payload: {"url": "<pdf_url>", "title": "research_paper_<timestamp>_<index>", "folder_name": "<topic-slug>"}
→ 30-second sleep between papers (rate limiting)

Step 5: Cap & Track
→ Hard-capped at 3 papers per run
→ Successful DOIs appended to processed_dois.txt

Step 6: Verification
→ Waits for n8n to finish conversion
→ Lists files in the topic folder
→ Verifies content quality (head -20 on each)
→ Marks task complete
```

### Script Internals (Key Code Logic)

**Topic folder resolution:**
```python
slug = re.sub(r'[^a-z0-9]+', '_', query.lower()).strip('_')
# Fuzzy match against existing folders (50% overlap threshold)
for folder in existing_folders:
    overlap = len(q_words & f_words) / max(len(q_words), len(f_words))
    if overlap >= 0.5:
        return folder  # reuses existing folder
return slug  # creates new folder
```

**Hallucination score for token pruning (HALL-OPT reference):**
```python
H_t = α·ℰ(Aₜ) + β·𝒰(pₜ) + γ·𝒞(Aₜ, A_ctx)
# where α, β, γ are learnable weights, converging to ~0.28, ~0.31, ~0.41
```

---

## 3. Analyst Worker

**Profile:** `analyst` — loaded from `~/.hermes/profiles/analyst/config.yaml`

**Model:** `deepseek/deepseek-v4-flash`

**Toolsets:** `terminal`, `kanban`, `file`

**Dependency:** Chained as parent=t_RESEARCHER_ID. Automatically promoted from `todo` to `ready` when the researcher completes.

### What It Does

1. Discovers the topic subfolder (not just the sandbox root — SYNTHESIS.md goes into the subfolder)
2. Reads all `research_paper_*.md` files
3. Compiles a structured literature matrix in SYNTHESIS.md with:
   - Frontmatter (create-date, type, tags, status)
   - Per-paper sections: core contribution, key innovations, experimental validation, results tables, limitations
   - Cross-paper synthesis table comparing paradigms
   - Research gaps and future directions
   - Unified literature matrix (dimension x paper comparison)
   - IEEE citations [1], [2], [3] and Obsidian wiki-links [[research_paper_*]]

---

## 4. n8n Service

**Endpoint:** `http://localhost:5678`

**Health check:** `GET /health` — returns HTTP 200 when running

**Webhook:** `POST /webhook/fetch-paper`
- Accepts `{"url": "<oa_pdf_url>", "title": "<filename>", "folder_name": "<topic-slug>"}`
- Downloads the PDF from the URL
- Forwards the file as multipart `file` to the **PyMuPDF4LLM microservice** (`POST http://localhost:5001/v1/convert/file`), which converts PDF→Markdown and returns it in the same JSON shape as before (`{"document": {"md_content": ...}}`) so the rest of the workflow is unchanged
- Writes to `<vault>/Research & Syntheses/<folder_name>/<title>.md`
- Returns `{"message": "Workflow was started"}`
- Response time: 1-3 minutes per paper (download + conversion)

**Known behavior:** n8n returns HTTP 200 even for unknown/misconfigured webhooks. The response body distinguishes them:
- `{"message": "Workflow was started"}` → working
- `{"message": "unknown webhook"}` or `"This webhook is not registered"` → not registered

---

## 5. Kanban Board

**Board name:** `academic-rag`

**Database:** `~/.hermes/kanban/boards/academic-rag/kanban.db`

**Task status lifecycle:**
```
Created → ready → (dispatch) → running → (completes) → done
                                            → (error, no PID) → reclaimed → ready → (re-dispatch) → running
                                            → (blocked by analyst) → unblocked → ready → (re-dispatch) → running
```

**Key commands:**
- `hermes kanban --board academic-rag create "..." --assignee <researcher|analyst> [--parent TASK_ID]`
- `hermes kanban --board academic-rag dispatch`
- `hermes kanban --board academic-rag list`
- `hermes kanban --board academic-rag log <TASK_ID>` (non-blocking snapshot)
- `hermes kanban --board academic-rag reclaim <TASK_ID>` (running → ready)
- `hermes kanban --board academic-rag unblock <TASK_ID>` (blocked → ready)
- `hermes kanban --board academic-rag archive <TASK_ID>...` (batch archive)

**Worker spawn location:** `~/.hermes/kanban/boards/academic-rag/workspaces/<TASK_ID>/`

---

## 6. Deduplication Tracker

**File:** `~/.hermes/processed_dois.txt`

**Format:** One DOI per line, plain text:
```
10.1038/s41598-026-42981-3
10.1007/s43684-026-00130-7
10.1007/s44196-026-01236-9
```

**Behavior:** Persists across pipeline runs. DOIs accumulate and are never re-processed. To reset for fresh runs, delete the file.

---

## 7. External APIs

### Elsevier Scopus Search API
- **Endpoint:** `https://api.elsevier.com/content/search/scopus`
- **Auth:** `X-ELS-APIKey` header (value from `ELSEVIER_API_KEY` env var)
- **Rate limit:** Free tier: ~20 requests/second (generous)
- **Query syntax:** Standard Scopus field codes, Boolean operators
- **Response fields used:** `search-results.entry[].prism:doi`

### Unpaywall
- **Endpoint:** `https://api.unpaywall.org/v2/{doi}?email=your-email@example.com`
- **Auth:** None (email-based rate limiting)
- **Rate limit:** Free tier: ~100K requests/day
- **Response fields used:** `best_oa_location.url_for_pdf`, `oa_locations[0].url_for_pdf`, `title`, `year`, `genre`

## Related Documentation

- [[00_Overview]] — System overview
- [[02_Pipeline_Flow]] — Step-by-step execution flow
- [[03_Configuration]] — Profile setup, API keys, n8n configuration
- [[04_Operational_Guide]] — Running the pipeline
- [[05_Troubleshooting]] — Common issues and recovery
- [[06_Reference]] — Commands, file paths, API endpoints