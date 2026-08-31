# Docker Volume Mount Recovery for n8n

When n8n's Read/Write Files node errors with `ENOENT: no such file or directory, realpath '/workspace/obsidian_brain/...'`, the root cause is almost always a missing or stale Docker volume mount inside the n8n container.

## Symptom Checklist

- [ ] n8n health endpoint returns 200
- [ ] Webhook POST returns `{"message":"Workflow was started"}`
- [ ] n8n error log shows `ENOENT` on `/workspace/obsidian_brain/...`
- [ ] `docker exec n8n_automation ls /workspace/` → `No such file or directory`
- [ ] `docker inspect n8n_automation` shows no mount for `/workspace`
- [ ] `cat ~/n8n/docker-compose.yml` has the mount line but container was created before it was added

## Root Cause

The docker-compose.yml at `~/n8n/docker-compose.yml` declares:

```yaml
volumes:
  - ~/workspace:/workspace
```

But **docker-compose.yml changes are not automatically applied to running containers**. If the container was created from an older version of the compose file that lacked this mount, the new mount line is ignored until the container is recreated.

## Recovery Procedure

### Step 1: Recreate the container

```bash
# Remove the old container (data volumes are in ./n8n_data/ — safe)
docker rm -f n8n_automation

# Recreate with current compose file
cd ~/n8n && docker compose up -d
```

### Step 2: Verify the mount

```bash
# Wait for container to be healthy
sleep 5

# Check the workspace mount
docker exec n8n_automation ls /workspace/obsidian_brain/
# Expected: Research & Syntheses  constitution.md

# Check a subfolder
docker exec n8n_automation ls "/workspace/obsidian_brain/Research & Syntheses/"
```

### Step 3: Re-send lost webhook payloads

Container recreation discards any queued or in-flight webhook requests. The researcher ran the Python script and sent DOIs to the old container — those requests are lost. Re-send them:

```bash
# Read the DOIs from the tracker, skip the old ones (from previous runs)
python3 -c "
import os, urllib.request, json, time

# These are the DOIs from the current run (last 2-3 entries in the tracker)
# Replace with actual DOIs from the current session
dois = [
    '10.1057/s41599-026-06632-2',
    '10.1038/s41597-026-07484-w'
]
folder_name = 'asymmetric_effect_of_oil_price_shocks_on_real_economy_real_output'

for i, doi in enumerate(dois):
    upw_url = f'https://api.unpaywall.org/v2/{doi}?email=your-email@example.com'
    try:
        with urllib.request.urlopen(upw_url, timeout=30) as r:
            upw_data = json.loads(r.read().decode())
        pdf_url = (upw_data.get('best_oa_location') or {}).get('url_for_pdf')
        if pdf_url:
            payload = json.dumps({
                'url': pdf_url,
                'title': f'research_paper_{int(time.time())}_{i}',
                'folder_name': folder_name
            }).encode()
            n8n_req = urllib.request.Request(
                'http://localhost:5678/webhook/fetch-paper',
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(n8n_req, timeout=30) as n8n_resp:
                print(f'DOI {doi} -> {n8n_resp.read().decode()}')
        else:
            print(f'DOI {doi} -> No OA PDF found')
    except Exception as e:
        print(f'DOI {doi} -> Error: {e}')
    if i < len(dois)-1:
        time.sleep(5)
"
```

### Step 4: Wait for n8n to process

```bash
sleep 30
ls -la "<vault>/Research & Syntheses/$folder_name/"
```

### Step 5: Fix the analyst worker

If the analyst already spawned and blocked on the empty directory:

```bash
hermes kanban --board academic-rag unblock t_ANALYST_TASK_ID
hermes kanban --board academic-rag dispatch
```

## Prevention

Before each pipeline run, the pre-flight check should verify the mount is active:

```bash
docker exec n8n_automation ls /workspace/obsidian_brain/ 2>/dev/null || {
  echo "ERROR: n8n container missing workspace volume mount"
  echo "Fix: docker rm -f n8n_automation && cd ~/n8n && docker compose up -d"
  exit 1
}
```