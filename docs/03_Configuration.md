---
create-date: 2026-07-05
type: documentation
status: active
tags:
  - literature-rag/system-documentation
---

# Configuration

## 1. ESLSEVIER API Key

The researcher worker requires an Elsevier API key to query the Scopus Search API. This key must be set as an environment variable **before** the Kanban dispatcher spawns the worker (the worker inherits the orchestrator's environment).

**Setting the key:**

```bash
# In ~/.hermes/.env (recommended — loaded automatically by Hermes)
ELSEVIER_API_KEY=your_api_key_here

# Or export before starting the pipeline
export ELSEVIER_API_KEY=your_api_key_here
```

**Where to get one:** [Elsevier Developer Portal](https://dev.elsevier.com/) — free tier available.

**Verification:**
```bash
python3 -c "
import os, urllib.parse, urllib.request, json
query = 'machine+learning'
url = 'https://api.elsevier.com/content/search/scopus?query=' + urllib.parse.quote(query) + '&field=prism:doi&count=5'
req = urllib.request.Request(url, headers={'X-ELS-APIKey': os.environ.get('ELSEVIER_API_KEY',''), 'Accept': 'application/json'})
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read().decode())
    print(f'Scopus returned {len(data[\"search-results\"][\"entry\"])} results')
"
```

**Failure symptom:** The researcher's log shows `Scopus Error: ...` and the task stays in `running` with no PID.

---

## 2. Researcher Profile Configuration

**File:** `~/.hermes/profiles/researcher/config.yaml`

```yaml
model:
  provider: openrouter
  default: deepseek/deepseek-v4-flash    # Was poolside/laguna-m.1:free — changed due to rate limiting
  temperature: 0.5
  top_p: 0.95
  max_tokens: 16384
  extra_body:
    reasoning:
      enabled: true
toolsets:
  - terminal
  - kanban
agent:
  max_turns: 20
  verbose: false
onboarding:
  seen:
    tool_progress_prompt: true
```

**Critical setting:** `model.default` — must point to a working model (not rate-limited). The original `poolside/laguna-m.1:free` was consistently HTTP 429 on OpenRouter. Changed to `deepseek/deepseek-v4-flash`.

**To view active profiles:**
```bash
ls ~/.hermes/profiles/
cat ~/.hermes/profiles/researcher/config.yaml
```

---

## 3. Analyst Profile Configuration

**File:** `~/.hermes/profiles/analyst/config.yaml`

```yaml
model:
  provider: openrouter
  default: deepseek/deepseek-v4-flash
  temperature: 0.3
  top_p: 0.95
  max_tokens: 16384
  extra_body:
    reasoning:
      enabled: true
toolsets:
  - terminal
  - kanban
agent:
  max_turns: 25
  verbose: false
onboarding:
  seen:
    tool_progress_prompt: true
```

Note the higher `max_turns` (25 vs 20) — the analyst reads multiple files and writes a comprehensive synthesis, which requires more turns.

---

## 4. n8n Configuration

**n8n is a local service.** Verify it's running and the webhook workflow is registered:

```bash
# Health check
curl -s http://localhost:5678/health

# Webhook verification (read the response BODY, not just status code)
curl -s -X POST -H "Content-Type: application/json" -d '{}' http://localhost:5678/webhook/fetch-paper
```

**Expected response:** `{"message":"Workflow was started"}`
**Bad response:** `"This webhook is not registered"`

### If the Webhook Is Not Registered

The n8n workflow needs a Webhook trigger node matching `/fetch-paper`, followed by a PDF download step and a conversion step that forwards the downloaded file to the **PyMuPDF4LLM microservice** (`POST http://localhost:5001/v1/convert/file`). The exact n8n workflow configuration is outside this document's scope, but the trigger node must have:

- **Method:** POST
- **Path:** `fetch-paper`
- **Response:** `Workflow was started`

---

## 5. Vault Directory

The pipeline writes converted Markdown files to a sandbox directory that doubles as the Obsidian vault:

```bash
<vault>/Research & Syntheses/
```

This directory must exist and be writable. The orchestrator creates it during pre-flight:

```bash
mkdir -p "<vault>/Research & Syntheses/"
```

Each pipeline run creates a **topic-specific subfolder** inside this directory:

```
Research & Syntheses/
├── token_optimization_and_pruning_methods_for_large_language_models/
│   ├── research_paper_1783255564_0.md
│   ├── research_paper_1783255596_1.md
│   ├── research_paper_1783255627_2.md
│   └── SYNTHESIS.md
└── <future-topic>/
    └── ...
```

---

## 6. Kanban Board

**Board name:** `academic-rag`

The board is persistent across sessions. Its database lives at:

```
~/.hermes/kanban/boards/academic-rag/kanban.db
```

Worker workspace directories (created at dispatch time):

```
~/.hermes/kanban/boards/academic-rag/workspaces/t_<TASK_ID>/
```

---

## 7. Deduplication Tracker

**File:** `~/.hermes/processed_dois.txt`

This file is created by the researcher worker and accumulates DOIs that were successfully resolved and sent to n8n. It persists across pipeline runs.

**To inspect:**
```bash
cat ~/.hermes/processed_dois.txt
```

**To reset (clear all processed DOIs):**
```bash
rm ~/.hermes/processed_dois.txt
```

**To disable deduplication temporarily:** Delete the file before each run, or set it to be read-only before the pipeline starts.

---

## 8. Unpaywall Configuration

Unpaywall is used with no API key — just an email identifier:

```
https://api.unpaywall.org/v2/{doi}?email=your-email@example.com
```

The email address identifies the application to Unpaywall for rate limiting and debugging purposes. Change it by editing the Python script's `email=` parameter if desired.

## Related Documentation

- [[00_Overview]] — System overview
- [[01_Pipeline_Components]] — Component descriptions
- [[02_Pipeline_Flow]] — Step-by-step execution flow
- [[04_Operational_Guide]] — Running the pipeline
- [[05_Troubleshooting]] — Common issues and recovery
- [[06_Reference]] — Commands, file paths, API endpoints