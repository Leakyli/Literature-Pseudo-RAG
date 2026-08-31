# PyMuPDF4LLM PDF → Markdown Microservice

Minimal Flask service that converts an uploaded PDF to Markdown using PyMuPDF4LLM.
CPU-only — no GPU needed (the reason it replaced a local Docling OCR model,
which took ~30 min/PDF on a VPS; this takes seconds).

- `POST /v1/convert/file` — multipart form field `file`
- Returns `{"document": {"md_content": "..."}}` — the same JSON shape as the
  Docling API it replaced, so the n8n workflow was unchanged by the swap.

Run:

```bash
docker compose up --build pdf_service     # exposes port 5001
```