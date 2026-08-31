---
create-date: 2026-07-05
type: documentation
status: active
tags:
  - literature-rag/system-documentation
---

# Literature RAG System — Overview

The **Literature RAG (Retrieval-Augmented Generation)** system is an automated pipeline that discovers open-access academic papers on a user-specified topic, converts them to Markdown (via a PyMuPDF4LLM microservice), and synthesizes a structured literature matrix. It operates as a multi-agent workflow orchestrated via Hermes Kanban boards, backed by real API integrations (Elsevier Scopus, Unpaywall) and a local n8n + PyMuPDF4LLM conversion pipeline.

## Architecture at a Glance

```
┌──────────────────────────────────────────────────────────┐
│                    User Request                           │
│   "Token optimization and pruning methods for LLMs"      │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│             Orchestrator (this Hermes session)            │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Pre-flight: n8n health, webhook, vault dir        │  │
│  │  Kanban: create researcher + analyst tasks          │  │
│  │  Dispatch: spawn workers sequentially               │  │
│  └────────────────────────────────────────────────────┘  │
└──────────┬───────────────────────────────────┬───────────┘
           │                                   │
           ▼                                   ▼
┌─────────────────────────┐    ┌───────────────────────────┐
│   Researcher Worker     │    │     Analyst Worker         │
│   (profile: researcher) │    │   (profile: analyst)       │
│                         │    │                            │
│  1. Query Scopus API    │    │  1. Read Markdown files    │
│  2. Resolve DOIs via    │    │  2. Compile literature     │
│     Unpaywall           │    │     matrix                 │
│  3. Stream PDF URLs to  │    │  3. Write SYNTHESIS.md     │
│     n8n webhook         │    │                            │
│  4. Wait for conversion │    │                            │
└────────────┬────────────┘    └───────────────────────────┘
             │                             ▲
             ▼                             │
┌─────────────────────────┐                │
│     n8n (local)         │────────────────┘
│                         │
│  /webhook/fetch-paper   │
│  Download PDFs          │
│  Forward → PyMuPDF4LLM  │──► host :5001 /v1/convert/file
│  Write to topic folder  │
└─────────────────────────┘
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Kanban-based orchestration** | Hermes Kanban provides dependency chaining (parent/child tasks), status tracking, and automatic worker spawning without custom scheduling code. |
| **Separate researcher + analyst profiles** | Each profile has its own config (model, temperature, toolsets), preventing resource conflicts and allowing independent tuning. |
| **PyMuPDF4LLM PDF→Markdown microservice** | Pipeline avoids doing heavy document processing inline. n8n downloads the PDF and forwards it to a dedicated **PyMuPDF4LLM microservice** (host `:5001`, `POST /v1/convert/file`) that converts PDF→Markdown. PyMuPDF4LLM is CPU-only, so it needs no GPU. |
| **Deduplication via processed_dois.txt** | Prevents re-processing the same DOI across multiple runs, respecting API rate limits and avoiding redundant n8n work. |
| **3-paper hard cap per run** | Limits per-run scope to stay within free-tier API quotas (Unpaywall, Scopus) and n8n processing capacity. |
| **30-second cooldown between papers** | Prevents overwhelming the n8n → PyMuPDF4LLM conversion pipeline with concurrent requests. |

## System Requirements

- **Hermes Agent** with Kanban boards enabled
- **n8n** running locally on port 5678 with a `/webhook/fetch-paper` workflow
- **PyMuPDF4LLM PDF→Markdown microservice** (Flask) running on host port 5001 with a `POST /v1/convert/file` endpoint
- **Elsevier API Key** (`ELSEVIER_API_KEY` in environment)
- **Unpaywall** (free tier, no API key needed — uses email `your-email@example.com`)
- **Python 3** with standard library only (urllib, json, time, re)
- **Vault directory:** `<vault>/Research & Syntheses/`

## Related Documentation

- [[01_Pipeline_Components]] — Detailed component descriptions
- [[02_Pipeline_Flow]] — Step-by-step execution flow
- [[03_Configuration]] — Profile setup, API keys, n8n configuration
- [[04_Operational_Guide]] — Running the pipeline
- [[05_Troubleshooting]] — Common issues and recovery
- [[06_Reference]] — Commands, file paths, API endpoints