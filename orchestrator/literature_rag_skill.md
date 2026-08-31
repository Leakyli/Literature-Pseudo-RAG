---
name: literature-rag
description: Populates the local SQLite Kanban board with historical open-access literature tasks via Scopus and Unpaywall.
category: Research
requires_toolsets:
  - terminal
required_environment_variables:
  - ELSEVIER_API_KEY  # Scopus Search API key — worker fails silently without it
required_commands:
  - curl  # health check
---

# Skill: Literature RAG Pipeline

When the user invokes this skill, you are an Orchestrator.

## Architectural Safeguards
1. You are strictly forbidden from reading raw data arrays, running scraping scripts, or processing PDF/HTML to Markdown yourself. These actions trigger context bloat.
2. If a worker gets blocked or errors, halt the pipeline and display the raw error log to the user. Do not attempt to play hero and complete the task yourself.

## Pre-flight Verification (run before dispatching any tasks)
1. Check that n8n is reachable: `curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/health` — must return 200.
2. Verify the fetch-paper webhook is actually registered in n8n by sending a test POST with an empty payload and examining the response body. n8n returns **HTTP 200** even for unknown webhooks, so a 200 status alone is a FALSE POSITIVE. Read the response body for "unknown webhook" or "This webhook is not registered" — if either appears, the webhook workflow does not exist and must be created in n8n first.
3. Ensure the sandboxed vault directory exists on the host: `mkdir -p "<vault>/Research & Syntheses/"`
4. **Verify n8n container can actually write to the workspace directory.** The volume mount in docker-compose.yml (`~/workspace:/workspace`) only takes effect when the container was created with that compose file. Check inside the container:
   ```bash
   docker exec n8n_automation ls /workspace/obsidian_brain/
   ```
   If this fails with "No such file or directory", the container is running without the mount. Fix by recreating:
   ```bash
   docker rm -f n8n_automation
   cd ~/n8n && docker compose up -d
   ```
   Then re-run the check. Without this mount, n8n's Read/Write Files node errors with ENOENT — every webhook call succeeds (200) but the file write silently fails.
5. If any pre-flight check fails, stop; do not create tasks or dispatch.

## Operational Steps

> **Path note**: The researcher's generated Python script creates a topic-specific subfolder under the Obsidian Vault sandbox `<vault>/Research & Syntheses/` (e.g., `token_optimization_and_pruning_methods_for_large_language_models/`). SYNTHESIS.md is written into that subfolder, not the root of the sandbox. The task descriptions below use the general path — the actual file will be found under the topic folder.

> **Timing note**: n8n takes time (often 1-3 minutes) to convert PDFs to Markdown. The researcher task typically finishes before n8n deposits files. If the analyst spawns immediately, it will find an empty directory and may exhaust its iteration budget. If this happens, reclaim/unblock the analyst and re-dispatch — the files will be present on the retry.

1. Ensure the project board is initialized:
   hermes kanban boards create academic-rag --name "Academic Literature RAG"

2. **Archive prior-run tasks (critical).** Before creating any new tasks, list the board and archive every task from the previous run:
   ```
   hermes kanban --board academic-rag list
   hermes kanban --board academic-rag archive TASK_ID_1 TASK_ID_2 TASK_ID_3 ...
   ```
   Leftover tasks with the same assignee on the same board can conflict with new ones, and the dispatcher may refuse to promote them. Archive accepts multiple IDs in one call — batch them all.
   If the board is clean (no tasks), skip this step.

3. Create the researcher task:
   hermes kanban --board academic-rag create "Query the Elsevier Scopus Search API for papers regarding: {{input}}. DO NOT restrict searches to a specific year. If brand-new papers lack open-access links, target older foundational papers. Extract DOIs, resolve them via Unpaywall, and stream the URLs directly to http://localhost:5678/webhook/fetch-paper to let n8n handle the conversion to Markdown files inside <vault>/Research & Syntheses/." --assignee researcher

   **For narrow/specific topics:** Append fallback alternative queries as a bullet list so the researcher can iterate if the primary query returns 0 OA-relevant results. Example:
   ```
   If the primary query returns fewer than 4 open-access DOIs, try these alternative queries in sequence until 4 papers are found:
   1. 'broader_synonym_1 AND core_concept'
   2. 'broader_synonym_2 AND output'
   3. 'alternative_phrasing'
   ```

   **Paper count cap:** The researcher's generated Python script defaults to `sent_count >= 3` (3 papers maximum). To increase this, append an explicit instruction to the task description:
   ```
   Increase the sent_count cap from 3 to N — you must send at least N papers to n8n.
   ```

4. Create the dependent analyst task, chained to the researcher:
   hermes kanban --board academic-rag create "Read the processed Markdown files inside <vault>/Research & Syntheses/ and compile a detailed literature matrix into SYNTHESIS.md. Write the output to <vault>/Research & Syntheses/SYNTHESIS.md." --assignee analyst --parent FIRST_TASK_ID

   Note: The actual output path will be inside the topic subfolder (e.g., <vault>/Research & Syntheses/topic-name/SYNTHESIS.md). The analyst agent discovers the correct folder dynamically.

5. Automatically execute the dispatcher. After this, the researcher worker spawns. The analyst task remains `todo` until the researcher completes:
   hermes kanban --board academic-rag dispatch

6. **Verify the worker actually spawned:**
   Immediately after dispatch, run `hermes kanban --board academic-rag list` and check the first task transitioned from `ready` to `running`. Then confirm a worker process exists:
   ```
   ps aux | grep 't_TASK_ID' | grep -v grep
   ```
   Dispatch's "Spawned: N" summary can report **0 even when the spawn succeeded** — always verify via `list` + `ps`, not the dispatch summary alone.

7. **Run dispatch AGAIN after the researcher finishes.** The dispatcher only spawns ready tasks. When the researcher completes, its child (analyst) gets promoted to `ready` but won't spawn until you dispatch again:
   ```
   hermes kanban --board academic-rag dispatch
   ```
   Then verify the analyst spawned via `list` + `ps` (same check as step 6).

## Pitfalls & Troubleshooting

1. **Stopping a running worker:** `kill PID` (SIGTERM) often does not stop kanban-spawned researcher workers. Always use `kill -9 PID` (SIGKILL). After killing, confirm with `ps aux | grep t_TASK_ID` — exit code 1 (no match) means clean kill.

2. **Researcher profile model is rate-limited (HTTP 429):** Kanban workers run under the profile matching their `--assignee` label. The researcher uses `~/.hermes/profiles/researcher/config.yaml`, the analyst uses `~/.hermes/profiles/analyst/config.yaml`. If the model in that profile is a free-tier or oversubscribed endpoint (e.g., `poolside/laguna-m.1:free` on OpenRouter), every LLM call returns HTTP 429 and the worker dies instantly. The task shows `running` in the board but `ps aux | grep t_TASK_ID` finds no process. The log shows repeated `RateLimitError [HTTP 429]` across all 3 retries.

   **Fix:** Edit the profile's `config.yaml` to use a working model — usually the same model the main session uses:
   ```bash
   # Check current model
   cat ~/.hermes/profiles/researcher/config.yaml | grep default
   # By default, the model in researcher is nvidia/nemotron-3-ultra-550b-a55b:free
   # Update to a working model (e.g., deepseek/deepseek-v4-flash)
   # Edit the default: line in ~/.hermes/profiles/researcher/config.yaml
   ```
   Then reclaim the dead task and re-dispatch:
   ```bash
   hermes kanban --board academic-rag reclaim t_TASK_ID
   hermes kanban --board academic-rag dispatch
   ```
   Verify the new worker started with `list` + `ps` before assuming it's fixed. If the new worker also fails with a different error, check the log again — the model change fixed the rate limit but may expose other issues (missing API key, etc.).

3. **`hermes kanban tail TASK_ID` is blocking:** It follows the log in real-time and will hang your terminal until you Ctrl-C or it times out. For a one-shot snapshot of worker output, use `hermes kanban log TASK_ID` instead.

4. **`hermes kanban block TASK_ID --reason` is not supported:** The `block` subcommand does not accept a `--reason` flag. To annotate why a task was blocked, use `comment` instead.

5. **If a worker is stuck in `running` but no PID exists:** The worker likely died silently (Scopus API key missing, network error, etc.). Reclaim the task with `hermes kanban reclaim TASK_ID`, which resets it from `running` back to `ready` so dispatch can pick it up again. Before reclaiming, check the log with `hermes kanban --board academic-rag log TASK_ID` to understand why it failed — this often reveals a missing `ELSEVIER_API_KEY` or Unpaywall error.

6. **If a task is `blocked` (not `running`):** The `reclaim` command only works on tasks in `running` status. For blocked tasks, use `hermes kanban --board academic-rag unblock TASK_ID` instead — this returns them directly to `ready` so dispatch can pick them up. If the worker died while blocked, you can chain: `unblock` → `dispatch`.

7. **Analyst blocks after reading papers but before writing SYNTHESIS.md — timing race with n8n:** The researcher task finishes when the Scopus/Unpaywall Python script completes, but n8n may still be downloading and converting PDFs. If the analyst spawns during this window, it finds an empty directory and exhausts its iteration budget searching for files. By the time a second attempt spawns (via `unblock` → `dispatch`), the files will have arrived.

   **Mitigation:** If the analyst gets blocked after searching an empty directory:
   1. Check `ls "<vault>/Research & Syntheses/"` — if the topic subfolder exists and has `.md` files, the files have arrived.
   2. Run `hermes kanban --board academic-rag unblock t_TASK_ID`
   3. Run `hermes kanban --board academic-rag dispatch`
   4. Verify the new worker finds the files immediately.

8. **SYNTHESIS.md may land in root, not the topic subfolder — check both locations:** The analyst is tasked with writing to the root sandbox path (`<vault>/Research & Syntheses/SYNTHESIS.md`). In practice the file may land in the **root** of the sandbox OR inside the topic subfolder. Always check:
   ```bash
   find "<vault>/Research & Syntheses/" -name "SYNTHESIS.md"
   ```
   If there are two matches (one root, one subfolder), the root one may be stale from a previous run. Move the fresh one into the correct subfolder:
   ```bash
   mv "<vault>/Research & Syntheses/SYNTHESIS.md" \
      "<vault>/Research & Syntheses/<topic-folder>/SYNTHESIS.md"
   ```

9. **Need to re-dispatch for each stage:** The dispatcher only spawns tasks that are already `ready` when it runs. It does NOT auto-dispatch when a parent completes and promotes children. Run `hermes kanban --board academic-rag dispatch` after the researcher finishes to spawn the analyst.

10. **Researcher finished with 0 DOIs sent — diagnosing root cause:** The kanban log captures the agent's conversation summary but **not the Python script's stdout**. If the researcher claims "all DOIs were already processed or lacked OA PDFs" with no per-DOI trace visible, you cannot distinguish three failure modes from the log alone:

   - (A) Scopus returned 0 results (query too narrow)
   - (B) Scopus returned DOIs but Unpaywall found no OA PDFs for any
   - (C) The script crashed silently (expired key, rate limit, network timeout)

   **Diagnosis procedure:**
   1. Check `~/.hermes/processed_dois.txt` or `~/.hermes/processed_dois.txt` — if it exists, read its contents. If it doesn't exist, no DOI reached Unpaywall resolution at all.
   2. Run a manual Scopus query to see what DOIs the API returns:
      ```bash
      python3 -c "
      import os, urllib.parse, urllib.request, json
      query = '<the_original_query>'
      url = '[https://api.elsevier.com/content/search/scopus?query=](https://api.elsevier.com/content/search/scopus?query=)' + urllib.parse.quote(query) + '&field=prism:doi,dc:title&count=25'
      req = urllib.request.Request(url, headers={'X-ELS-APIKey': os.environ.get('ELSEVIER_API_KEY',''), 'Accept': 'application/json'})
      with urllib.request.urlopen(req) as r:
          data = json.loads(r.read().decode())
      entries = data.get('search-results', {}).get('entry', [])
      print(f'Total: {len(entries)}'); [print(f'  {e.get(\"prism:doi\",\"N/A\")} — {e.get(\"dc:title\",\"N/A\")[:80]}') for e in entries]
      "
      ```
   3. If Scopus returns entries but the deduplication file is empty, the issue is Unpaywall — resume the researcher's session (`hermes --resume <session> -p researcher`) and inspect the actual Unpaywall responses.
   4. If Scopus returned 0 entries, widen the query (drop niche acronyms, use broader synonyms).

11. **n8n works but Markdown files never arrive in the topic folder — missing Docker volume mount:** The docker-compose.yml at `~/n8n/docker-compose.yml` declares a bind mount from the host workspace to the container:
    ```yaml
    volumes:
      - ~/workspace:/workspace
    ```
    But if the container was **created before this line was added to compose**, the running container doesn't have this mount. Symptoms:
    - n8n webhook returns HTTP 200 `{"message":"Workflow was started"}`
    - n8n error log shows `ENOENT: no such file or directory, realpath '/workspace/obsidian_brain/Research & Syntheses/...'`
    - `docker exec n8n_automation ls /workspace/` fails with "No such file or directory"
    - The researcher's `processed_dois.txt` shows DOIs were sent, but the topic subfolder stays empty

    **Fix:** Recreate the container so the compose volume mount is applied:
    ```bash
    docker rm -f n8n_automation
    cd ~/n8n && docker compose up -d
    ```
    Then verify: `docker exec n8n_automation ls /workspace/obsidian_brain/`

    **Cascade effect:** The container recreation discards any queued webhook payloads. After fixing the mount, re-send the DOIs from the processed tracker:
    ```bash
    # Extract the 2-3 most recent DOIs from processed_dois.txt (not the previous run's entries)
    # Use the reference script at references/docker-volume-missing.md
    ```

12. **Researcher script has a hardcoded paper count cap (default 3):** The researcher agent's generated Python script uses `if sent_count >= 3: break` as the loop guard. When the user wants more than 3 papers, the orchestrator must explicitly say so in the task description:

    ```
    Increase the sent_count cap from 3 to N — you must send at least N papers to n8n.
    ```

    The researcher will then modify the generated script from `sent_count >= 3` to `sent_count >= N`. Without this explicit instruction, the cap stays at 3 regardless of what the task says about "send more papers."

13. **Scopus returns irrelevant OA PDFs — researcher sends papers unrelated to the topic:** Scopus relevance ranking combined with Unpaywall's OA-only filter can surface papers from adjacent disciplines that share keywords but are topically unrelated. Example: querying "oil price shocks AND real output" returned papers on nuclear energy welfare in Korea and a CO2 emissions dataset — keyword overlap but zero relevance.

    **Mitigations (in order of effectiveness):**
    - **Provide alternative query strings** in the task description (step 3 section). The researcher will iterate through them when OA availability is low.
    - **Ask the researcher to verify relevance** before sending. Append to the task:
      ```
      For each DOI, check its title against the topic. If the title is unrelated (energy mix, emissions, consumer behavior, etc. without oil price asymmetry), skip it and move to the next DOI.
      ```
    - **Use Scopus field codes** to scope the query to economics: append `&subj=ECON` to the Scopus URL or add `AND (LIMIT-TO(SUBJAREA,"ECON"))` to the query string.

14. **Hardcoded 30-second sleep between DOI submissions causes timeout on multi-query runs:** The researcher agent's script includes `time.sleep(30)` between each DOI submission to avoid rate-limiting n8n. When iterating through multiple queries (e.g., 5 queries × 4 DOIs × 30s = 10 minutes of wall time), the script runtime exceeds the 60-second default terminal timeout. The foreground command gets killed midway, the researcher retries from scratch, and no papers get through. Symptoms:
    - Log shows the same script being dispatched repeatedly with `0.0s` wall time references
    - `processed_dois.txt` doesn't get new entries
    - The process `ps` output shows the researcher alive but the kanban log shows no "Pipeline Finished" or "Success" lines

    **Fix:** Reduce the sleep to 5-10 seconds, or restructure so sleep only fires inside the `if sent_count > 0:` block (i.e., only between actual submissions, not on skipped DOIs). Include this hint in the task description when expecting multi-query iterations:
    ```
    Reduce the sleep time between DOI submissions to 5 seconds to avoid the 60-second timeout.
    ```

## Reference Files

- `references/researcher-worker-internals.md` — Full description of what the researcher agent's generated Python script actually does: Scopus query, DOI dedup, Unpaywall resolution, n8n streaming, rate limiting.
- `references/diagnosing-zero-doi-output.md` — Diagnosis workflow for when the researcher finishes with 0 DOIs sent: stdout capture gap, failure mode matrix, manual Scopus query command, session resume steps.
- `references/n8n-timing-race-recovery.md` — Timing race between researcher completion and n8n file delivery: symptoms, verification, recovery via `unblock` → `dispatch`, key commands reference.
- `references/docker-volume-missing.md` — Recovery when n8n container is missing the workspace volume mount: symptom detection, container recreate, DOI re-send procedure, analyst unblock.
- `references/multi-query-oil-price-asymmetry.md` — Case study: multi-query iteration strategy for narrow economics topics, including alternative query strings, sent_count cap override, and sleep timer reduction.
