---
create-date: 2026-07-05
type: documentation
status: active
tags:
  - literature-rag/system-documentation
---

# Pipeline Flow

## Phase 0: Pre-flight

The orchestrator performs these checks **before** creating any tasks:

1. **n8n health check:** `curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/health`
   - Must return `200`
   - If not 200, n8n is down — start it first

2. **Webhook verification:** `curl -s -X POST -H "Content-Type: application/json" -d '{}' http://localhost:5678/webhook/fetch-paper`
   - Must return `{"message": "Workflow was started"}`
   - HTTP 200 alone is a **false positive** — n8n returns 200 for unknown webhooks too
   - A response of `"unknown webhook"` or `"This webhook is not registered"` means the workflow doesn't exist

3. **Vault directory:** `mkdir -p "<vault>/Research & Syntheses/"`

If any check fails, the pipeline stops here.

---

## Phase 1: Board Initialization

```
hermes kanban boards create academic-rag --name "Academic Literature RAG"
```

Creates the board if it doesn't exist. Then checks for stale tasks from previous runs:

```
hermes kanban --board academic-rag list
hermes kanban --board academic-rag archive TASK_ID_1 TASK_ID_2 ...
```

Leftover tasks with the same assignee on the same board can cause conflicts — archive them all at once.

---

## Phase 2: Task Creation (Stage 1 — Researcher)

Two tasks are created:

```
# 1. Researcher task (ready)
hermes kanban --board academic-rag create \
  "Query the Elsevier Scopus Search API for papers regarding: <TOPIC>. \
   DO NOT restrict searches to a specific year. Extract DOIs, resolve them \
   via Unpaywall, and stream the URLs directly to http://localhost:5678/webhook/fetch-paper \
   to let n8n handle the download + Markdown conversion (via the PyMuPDF4LLM microservice) into files inside <vault>/Research & Syntheses/." \
  --assignee researcher

# 2. Analyst task (todo, parented to researcher)
hermes kanban --board academic-rag create \
  "Read the processed Markdown files inside <vault>/Research & Syntheses/ \
   and compile a detailed literature matrix into SYNTHESIS.md." \
  --assignee analyst --parent <RESEARCHER_TASK_ID>
```

The dependency chain: analyst stays `todo` until the researcher completes, then auto-promotes to `ready`.

---

## Phase 3: First Dispatch — Researcher Spawns

```
hermes kanban --board academic-rag dispatch
```

**Expected output:** `Spawned: 1 — t_<ID>  ->  researcher`

**Critical verification (the "Spawned: 1" number can be wrong):**
```
hermes kanban --board academic-rag list     # must show ● (running)
ps aux | grep t_<ID> | grep -v grep         # must return a PID
```

### What the Researcher Does (Autonomous)

```
┌─────────────────────────────────────────────┐
│ 1. Generate Python script                    │
│ 2. Execute: python3 <<'SCRIPT'              │
│    ├─ Resolve topic folder (slug + fuzzy)    │
│    ├─ Query Scopus API (25 results)          │
│    ├─ Load processed_dois.txt (dedup)        │
│    ├─ For each new DOI:                      │
│    │   ├─ Unpaywall resolution               │
│    │   ├─ If OA PDF found:                   │
│    │   │   ├─ POST to n8n webhook            │
│    │   │   ├─ Write DOI to tracker           │
│    │   │   └─ Sleep 30 seconds               │
│    │   └─ If no OA PDF: skip, log            │
│    └─ Cap at 3 papers → finish               │
│ 3. Wait for n8n files to appear              │
│ 4. Verify file content quality               │
│ 5. Mark task complete                        │
└─────────────────────────────────────────────┘
```

### Timing Race: Researcher vs n8n

The researcher's Python script completes as soon as all URLs are POSTed to n8n. But it takes 1–3 minutes per paper for n8n to download the PDF and convert it via the PyMuPDF4LLM microservice. The researcher handles this by adding a wait-and-verify step before marking complete.

---

## Phase 4: Second Dispatch — Analyst Spawns

Once the researcher is `done`, the analyst task auto-promotes to `ready`. The orchestrator must dispatch again:

```
hermes kanban --board academic-rag dispatch
```

**Expected output:** `Spawned: 1 — t_<ID>  ->  analyst`

**Verify:**
```
hermes kanban --board academic-rag list     # must show ● (running)
ps aux | grep t_<ID> | grep -v grep         # must return a PID
```

### What the Analyst Does (Autonomous)

```
┌──────────────────────────────────────────────┐
│ 1. Discover topic subfolder                  │
│ 2. Read all research_paper_*.md files        │
│ 3. For each paper, extract:                  │
│    ├─ Core contribution & innovation         │
│    ├─ Key results (tables, metrics)          │
│    ├─ Limitations acknowledged               │
│    └─ Cross-paper connections                │
│ 4. Compile SYNTHESIS.md:                     │
│    ├─ Frontmatter (dates, tags)              │
│    ├─ Per-paper deep sections                │
│    ├─ Cross-paper paradigm comparison        │
│    ├─ Unified literature matrix              │
│    └─ Research gaps & future directions      │
│ 5. Write to topic subfolder                  │
│ 6. Mark task complete                        │
└──────────────────────────────────────────────┘
```

---

## Phase 5: Retrieval

Once the synthesis exists in the topic subfolder, the user or orchestrator can query it directly (not via agents):

```
hermes kanban --board academic-rag list
cat "<vault>/Research & Syntheses/<TOPIC>/SYNTHESIS.md"
```

The `recall` skill provides a structured approach: locate the closest-matching topic folder, target SYNTHESIS.md (general query) or individual research_paper_*.md (specific question), read the file, and answer using only that content.

---

## State Machine Diagram

```
                    ┌──────────────┐
                    │  Pre-flight  │
                    └──────┬───────┘
                           │ pass
                           ▼
                    ┌──────────────┐
                    │ Board Init   │
                    └──────┬───────┘
                           │
                    ┌──────────────┐
                    │ Create Tasks │
                    │  researcher  │── (ready)
                    │  analyst     │── (todo)
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │  First Dispatch         │
              │  → researcher (running) │
              └────────────┬────────────┘
                           │
                    ┌──────────────┐
                    │ Researcher   │
                    │ works...     │
                    └──────┬───────┘
           ┌────────────────┤
           ▼                ▼
    ┌─────────────┐   ┌──────────────┐
    │ Complete ✓  │   │ Error/Dead  │
    │ (done)      │   │ (running,   │
    │ Analyst→ready│  │  no PID)    │
    └──────┬──────┘   └──────┬───────┘
           │                 │ reclaim
           ▼                 ▼
    ┌──────────────┐   ┌──────────────┐
    │ Second       │   │ Re-dispatch  │
    │ Dispatch     │   │ (researcher) │
    │ → analyst    │   └──────┬───────┘
    │   (running)  │          │
    └──────┬───────┘          ▼
           │            (back to running)
           ▼
    ┌──────────────┐
    │ Analyst      │
    │ works...     │
    └──────┬───────┘
           │
    ┌──────────────┐
    │ Complete ✓  │
    │ SYNTHESIS.md│
    │ written     │
    └──────────────┘
```

**Note:** The analyst can also get `blocked` (timing race with n8n, empty directory). Recovery path: `unblock` → `dispatch` — the files will be present on retry.

## Related Documentation

- [[00_Overview]] — System overview
- [[01_Pipeline_Components]] — Component descriptions
- [[03_Configuration]] — Profile setup, API keys, n8n configuration
- [[04_Operational_Guide]] — Running the pipeline
- [[05_Troubleshooting]] — Common issues and recovery
- [[06_Reference]] — Commands, file paths, API endpoints