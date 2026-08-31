# n8n Timing Race & Recovery Pattern

## The Race

The literature-rag pipeline has three actors that run asynchronously:

1. **Researcher worker** — queries Scopus, resolves DOIs via Unpaywall, streams URLs to n8n webhook
2. **n8n** — receives URLs, downloads PDFs, converts to Markdown, writes to `~/workspace/research/<topic>/`
3. **Analyst worker** — reads Markdown files from the topic directory, writes SYNTHESIS.md

The race: the researcher worker completes as soon as its Python script has sent all URLs to the n8n webhook. But n8n then takes 1-3 minutes to actually download and convert each PDF. If the analyst spawns during this window, it finds an empty directory and exhausts its iteration budget.

## Symptoms

- Analyst log shows repeated `ls`/`find` calls returning empty directories
- Analyst summary says "No processed Markdown files exist" despite researcher claiming "papers sent"
- Task is `blocked` after hitting 20/20 iteration budget

## Verification

```bash
# Check if files have arrived
ls -la ~/workspace/research/
ls -la ~/workspace/research/<topic-folder>/

# Check if analyst process is still alive
ps aux | grep 't_TASK_ID' | grep -v grep
```

## Recovery

If the analyst is blocked and files have now arrived:

```bash
# 1. Check the blocked task's log first
hermes kanban --board academic-rag log t_BLOCKED_TASK_ID | tail -20

# 2. Unblock (reclaim won't work on blocked tasks — use unblock)
hermes kanban --board academic-rag unblock t_BLOCKED_TASK_ID

# 3. Re-dispatch to spawn a fresh worker
hermes kanban --board academic-rag dispatch

# 4. Verify new worker is running and finding files
hermes kanban --board academic-rag list
ps aux | grep 't_TASK_ID' | grep -v grep
```

## Prevention

Currently, the researcher task completes before n8n finishes. Options to mitigate:

- **Manual delay**: Wait 2-3 minutes after the researcher completes before dispatching the analyst
- **Re-dispatch pattern**: Accept the timing race, then unblock + re-dispatch; the files will be present on retry
- The analyst agent on its second attempt (after unblock) finds files immediately and proceeds normally

## Key Commands Reference

| Situation | Command | Notes |
|-----------|---------|-------|
| Task `blocked` — unblock it | `hermes kanban --board academic-rag unblock t_ID` | Works on `blocked` status |
| Task `running` with no PID — reclaim | `hermes kanban --board academic-rag reclaim t_ID` | Only works on `running` status |
| Promote to `ready` manually | `hermes kanban --board academic-rag promote t_ID` | Recovery path for `todo`/`blocked` |
| Snapshot output (not stream) | `hermes kanban --board academic-rag log t_ID` | Non-blocking |
| Check worker exists | `ps aux \| grep t_ID \| grep -v grep` | Exit 1 = no worker |
| Find the SYNTHESIS.md | `find ~/workspace/research -name "SYNTHESIS.md"` | Written to topic subfolder |