---
create-date: 2026-07-05
type: documentation
status: active
tags:
  - literature-rag/system-documentation
---

# Reference

## Full Command Reference

### Kanban Board Management

| Action | Command | Notes |
|--------|---------|-------|
| Create board | `hermes kanban boards create academic-rag --name "Academic Literature RAG"` | Safe to run if exists |
| List tasks | `hermes kanban --board academic-rag list` | Shows status, assignee, title |
| Create task | `hermes kanban --board academic-rag create "<prompt>" --assignee <name> [--parent <ID>]` | Parent creates dependency chain |
| Dispatch | `hermes kanban --board academic-rag dispatch` | Spawns ready tasks only |
| Log snapshot | `hermes kanban --board academic-rag log <TASK_ID>` | Non-blocking, one-shot |
| Stream log | `hermes kanban tail <TASK_ID>` | Blocking — Ctrl-C or timeout |
| Reclaim | `hermes kanban --board academic-rag reclaim <TASK_ID>` | running → ready (for dead workers) |
| Unblock | `hermes kanban --board academic-rag unblock <TASK_ID>` | blocked → ready |
| Archive | `hermes kanban --board academic-rag archive <ID1> <ID2> ...` | Batch — accepts multiple IDs |
| Comment | `hermes kanban --board academic-rag comment <TASK_ID> "<text>"` | Annotate task |
| Complete | `hermes kanban --board academic-rag complete <TASK_ID>` | Manually mark done |

### Worker Management

| Action | Command | Notes |
|--------|---------|-------|
| Find worker PID | `ps aux \| grep t_<TASK_ID> \| grep -v grep` | No match = exit code 1 |
| Kill worker | `kill -9 <PID>` | SIGKILL required; SIGTERM may not work |
| Resume session | `hermes --resume <session_hash> -p researcher` | Resume dead worker's session |

### n8n

| Action | Command | Notes |
|--------|---------|-------|
| Health check | `curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/health` | Must return 200 |
| Webhook verify | `curl -s -X POST -H "Content-Type: application/json" -d '{}' http://localhost:5678/webhook/fetch-paper` | Must return `{"message":"Workflow was started"}` |

### Directory & File Management

| Action | Command | Notes |
|--------|---------|-------|
| Vault directory | `mkdir -p "<vault>/Research & Syntheses/"` | |
| List topic folders | `ls -1 "<vault>/Research & Syntheses/"` | |
| Find SYNTHESIS.md | `find "<vault>/Research & Syntheses/" -name "SYNTHESIS.md"` | Written to topic subfolder |
| Check tracker file | `cat ~/.hermes/processed_dois.txt 2>/dev/null` | Empty output = file doesn't exist |
| Reset dedup tracker | `rm ~/.hermes/processed_dois.txt` | Next run will re-process all DOIs |

### Profile Configuration

| Action | Command | Notes |
|--------|---------|-------|
| List profiles | `ls ~/.hermes/profiles/` | |
| View researcher profile | `cat ~/.hermes/profiles/researcher/config.yaml` | |
| View analyst profile | `cat ~/.hermes/profiles/analyst/config.yaml` | |

---

## API Endpoints

### Elsevier Scopus Search API

```
GET https://api.elsevier.com/content/search/scopus
```

**Parameters:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `query` | URL-encoded search string | Standard Scopus query syntax |
| `field` | `prism:doi,dc:title` | Controls returned fields |
| `count` | `25` | Max results per request |

**Headers:**
| Header | Value |
|--------|-------|
| `X-ELS-APIKey` | `$ELSEVIER_API_KEY` |
| `Accept` | `application/json` |

**Response structure:**
```json
{
  "search-results": {
    "entry": [
      {
        "prism:doi": "10.1038/s41598-026-42981-3",
        "dc:title": "Hallucination-aware learning and latency optimization transformer..."
      }
    ]
  }
}
```

### Unpaywall API

```
GET https://api.unpaywall.org/v2/{doi}?email=your-email@example.com
```

**No authentication required.** Email is used for rate limiting.

**Key response fields:**
| Field | Type | Description |
|-------|------|-------------|
| `best_oa_location.url_for_pdf` | string | Best OA PDF URL |
| `best_oa_location.url_for_landing_page` | string | Landing page for OA version |
| `oa_locations[0].url_for_pdf` | string | Fallback PDF URL |
| `title` | string | Paper title |
| `year` | integer | Publication year |
| `genre` | string | Type (journal-article, etc.) |

### n8n Webhook

```
POST http://localhost:5678/webhook/fetch-paper
Content-Type: application/json

{
  "url": "<oa_pdf_url>",
  "title": "research_paper_<timestamp>_<index>",
  "folder_name": "<topic-slug>"
}
```

**Response:** `{"message": "Workflow was started"}`

### PyMuPDF4LLM Microservice

```
POST http://localhost:5001/v1/convert/file
Content-Type: multipart/form-data
form field: file = <downloaded PDF>
```

**Request:** Multipart upload of the PDF file (sent by n8n after download).
**Response:**

```json
{
  "document": {
    "md_content": "<converted markdown>"
  }
}
```

| Parameter | Value | Description |
|-----------|-------|-------------|
| `file` | multipart binary | The PDF to convert |

**Notes:** Flask service on the host (not Docker), CPU-only via `pymupdf4llm`. Returns the same JSON shape as before so the n8n workflow is unchanged.

---

## File Paths

| Resource | Path |
|----------|------|
| Kanban board DB | `~/.hermes/kanban/boards/academic-rag/kanban.db` |
| Worker workspaces | `~/.hermes/kanban/boards/academic-rag/workspaces/t_<ID>/` |
| Researcher profile | `~/.hermes/profiles/researcher/config.yaml` |
| Analyst profile | `~/.hermes/profiles/analyst/config.yaml` |
| Vault directory | `<vault>/Research & Syntheses/` |
| PyMuPDF4LLM microservice | `pdf_service/server.py` (Flask, host :5001) |
| DOI dedup tracker | `~/.hermes/processed_dois.txt` |
| Literature RAG skill | `~/.hermes/skills/research/literature-rag/SKILL.md` |
| Skill reference files | `~/.hermes/skills/research/literature-rag/references/` |
| Hermes config | `~/.hermes/config.yaml` |

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ELSEVIER_API_KEY` | Yes | Scopus Search API authentication |
| `HERMES_CONFIG` | No | Alternate Hermes config path |

---

## Common Query Phrases by Topic

| Topic | Effective Query |
|-------|----------------|
| XAI / Explainability | `explainable AI OR interpretable machine learning OR XAI deep learning breast cancer detection` |
| Token optimization | `token optimization AND pruning AND large language models` |
| Model compression | `model compression OR network pruning OR quantization large language models` |

---

## Terminology

| Term | Definition |
|------|------------|
| **n8n** | Local workflow automation service that orchestrates PDF download + Markdown conversion via the PyMuPDF4LLM microservice |
| **DOI** | Digital Object Identifier — unique paper identifier |
| **OA** | Open Access — freely available academic paper |
| **Unpaywall** | API that finds OA versions of paywalled papers |
| **Scopus** | Elsevier's abstract and citation database |
| **Kanban** | Hermes project management board for task orchestration |
| **Deduplication** | Skipping previously-processed DOIs via tracker file |
| **SYNTHESIS.md** | The final output — structured literature matrix |

## Related Documentation

- [[00_Overview]] — System overview
- [[01_Pipeline_Components]] — Component descriptions
- [[02_Pipeline_Flow]] — Step-by-step execution flow
- [[03_Configuration]] — Profile setup, API keys, n8n configuration
- [[04_Operational_Guide]] — Running the pipeline
- [[05_Troubleshooting]] — Common issues and recovery