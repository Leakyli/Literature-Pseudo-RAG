#!/usr/bin/env python3
"""
Researcher worker logic: Scopus -> Unpaywall -> n8n webhook -> PyMuPDF4LLM.

This is a sanitized, runnable template of the script the Researcher worker
generates on each run. Replace placeholders / set env vars before use.

Required environment variables:
  ELSEVIER_API_KEY   - Scopus Search API key (https://dev.elsevier.com)
  UNPAYWALL_EMAIL    - email used for Unpaywall API attribution
  N8N_WEBHOOK_URL    - your n8n webhook, e.g. http://localhost:5678/webhook/fetch-paper

Optional:
  OUTPUT_DIR         - where the topic folder will be created (default ./vault/Research & Syntheses)
  PROCESSED_DOIS_FILE- dedup tracker path (default ./processed_dois.txt)
"""
import os, urllib.parse, urllib.request, json, time, re

query = "oil price asymmetry output effects"  # <-- change to your research topic
base_dir = os.environ.get("OUTPUT_DIR", "./vault/Research & Syntheses")


# 1. Fuzzy Folder Matching & Creation Logic
def resolve_topic_folder(q, b_dir):
    slug = re.sub(r'[^a-z0-9]+', '_', q.lower()).strip('_')
    if os.path.exists(b_dir):
        existing_folders = [f for f in os.listdir(b_dir) if os.path.isdir(os.path.join(b_dir, f))]
        stop_words = {'for', 'and', 'the', 'with', 'using', 'methods', 'techniques', 'llm', 'llms', 'ai'}
        q_words = set(slug.split('_')) - stop_words

        for folder in existing_folders:
            f_words = set(folder.split('_')) - stop_words
            if q_words and f_words:
                overlap = len(q_words.intersection(f_words)) / max(len(q_words), len(f_words))
                if overlap >= 0.5:
                    print(f"Fuzzy Match Found! Reusing existing folder: {folder}")
                    return folder
    return slug


folder_name = resolve_topic_folder(query, base_dir)
target_folder_path = os.path.join(base_dir, folder_name)
os.makedirs(target_folder_path, exist_ok=True)
os.chmod(target_folder_path, 0o777)

# 2. Fetch Papers
scopus_url = "https://api.elsevier.com/content/search/scopus?query=" + urllib.parse.quote(query) + "&field=prism:doi&count=25"
req = urllib.request.Request(scopus_url, headers={"X-ELS-APIKey": os.environ["ELSEVIER_API_KEY"], "Accept": "application/json"})

# 3. Deduplication Tracker
tracker_file = os.environ.get("PROCESSED_DOIS_FILE", "processed_dois.txt")
seen_dois = set()
if os.path.exists(tracker_file):
    with open(tracker_file, "r") as f:
        seen_dois = set(line.strip() for line in f if line.strip())

try:
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
    dois = [e.get("prism:doi") for e in data.get("search-results", {}).get("entry", []) if e.get("prism:doi")]
    print(f"Found DOIs: {dois}")
    print(f"Already seen: {seen_dois}")

    sent_count = 0
    for doi in dois:
        if sent_count >= 3:  # paper count cap, adjust as needed
            break
        if doi in seen_dois:
            print(f"Skipping already seen: {doi}")
            continue

        upw_url = f"https://api.unpaywall.org/v2/{doi}?email={os.environ.get('UNPAYWALL_EMAIL', 'your-email@example.com')}"
        try:
            with urllib.request.urlopen(upw_url) as r2:
                upw_data = json.loads(r2.read().decode())
                pdf_url = (upw_data.get("best_oa_location") or {}).get("url_for_pdf")

                if pdf_url:
                    file_id = f"{int(time.time())}_{sent_count}"
                    payload = json.dumps({
                        "url": pdf_url,
                        "title": f"research_paper_{file_id}",
                        "folder_name": folder_name
                    }).encode()

                    n8n_req = urllib.request.Request(
                        os.environ.get("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/fetch-paper"),
                        data=payload, headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(n8n_req)
                    print(f"Success: Sent {doi} to folder '{folder_name}' via n8n.")

                    with open(tracker_file, "a") as f:
                        f.write(doi + "\n")
                    seen_dois.add(doi)
                    sent_count += 1

                    if sent_count < 3:
                        time.sleep(5)
                else:
                    print(f"No PDF found for {doi}")
        except Exception as e:
            print(f"Error fetching {doi}: {e}")
    print(f"\nPipeline Finished: {sent_count} papers sent.")
except Exception as e:
    print(f"Scopus Error: {e}")