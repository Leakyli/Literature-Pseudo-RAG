# Researcher Worker Internals

When the kanban dispatcher spawns the researcher worker, it runs as a standalone Hermes agent with the `researcher` profile. The agent generates and executes a Python script that performs the following pipeline:

## Pipeline Steps

1. **Scopus Search** — Queries `https://api.elsevier.com/content/search/scopus` with the user's topic, requesting 25 results with DOI fields. Uses `ELSEVIER_API_KEY` from environment.

2. **DOI Deduplication** — Checks `~/.hermes/processed_dois.txt` (persistent across runs) to skip DOIs already sent in prior sessions.

3. **Unpaywall Resolution** — For each new DOI, calls `https://api.unpaywall.org/v2/{doi}?email=your-email@example.com` to find the best OA PDF URL (`best_oa_location.url_for_pdf`).

4. **n8n Streaming** — Sends found PDF URLs as JSON payloads to `http://localhost:5678/webhook/fetch-paper` with `{"url": "...", "title": "research_paper_{timestamp}_{index}"}`.

5. **Rate Limiting** — Applies a 30-second cooldown between papers to avoid overwhelming n8n/Docling. Hard-capped at 3 papers per run.

6. **Tracking** — Logs successfully-sent DOIs to `~/.hermes/processed_dois.txt` so they're never re-processed.

## Failure Modes

- **Missing ELSEVIER_API_KEY** — The Scopus call raises an exception, script exits with `Scopus Error: ...`. Worker terminates silently, task stays stuck in `running`.
- **Unpaywall timeout/403** — Individual DOI failures are caught and logged, pipeline continues to next DOI.
- **n8n unreachable** — The POST to fetch-paper webhook fails; the error is caught per-DOI and logged.

## Verification

After a few minutes of a researcher being in `running`, always check:
- Worker PID exists (`ps aux | grep t_TASK_ID | grep -v grep`)
- Worker log for errors (`hermes kanban --board academic-rag log TASK_ID`)
- The `~/workspace/research/` directory for arriving Markdown files