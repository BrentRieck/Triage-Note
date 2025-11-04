# Clinician Helper

FastAPI web application that helps healthcare professionals summarize clinical notes and draft telephone triage question lists using the OpenAI Chat Completions API.

## Features

- **Summarize Notes:** Convert messy, unstructured clinical notes into concise professional documentation.
- **Triage Questions:** Turn patient call transcripts into prioritized triage question checklists.
- Minimal HTML UI for quick testing and REST API endpoints for integration.

## Prerequisites

- Python 3.11+
- OpenAI API key (`OPENAI_API_KEY`).
- Optional: Custom model overrides for summarization (`OPENAI_MODEL_SUMMARIZE`) and triage (`OPENAI_MODEL_TRIAGE`). Defaults use GPT-4.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_openai_key
# Optional overrides if you prefer specific models
export OPENAI_MODEL_SUMMARIZE=gpt-4o-mini
export OPENAI_MODEL_TRIAGE=gpt-4o-mini
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000 to use the UI.

## API Endpoints

- `POST /api/summarize` → `{ "text": "..." }` → `{ "summary": "..." }`
- `POST /api/triage` → `{ "text": "..." }` → `{ "questions": ["..."] }`

Both endpoints accept an optional `stream` boolean flag to request server-sent event (SSE) responses (UI currently uses non-streaming mode).

## Deployment on Render

This repository ships with a `render.yaml` that provisions a web service:

```yaml
services:
  - type: web
    name: clinician-helper
    env: python
    plan: starter
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

Set the following environment variables in Render (marked as `sync: false` in the manifest so they are provided via the dashboard):

- `OPENAI_API_KEY`
- `OPENAI_MODEL_SUMMARIZE` (optional)
- `OPENAI_MODEL_TRIAGE` (optional)

For environments subject to HIPAA or similar requirements, deploy into a HIPAA-enabled Render workspace and enable data-handling safeguards for your OpenAI account (e.g., enterprise privacy controls).

## Prompt Engineering

System prompts for summarization and triage live in `app/prompts.py`. The OpenAI client injects these automatically before sending user text, ensuring consistent behavior across local development and deployment.

## Security Notes

- Never commit API keys. Use environment variables locally and in deployment.
- If handling PHI, ensure the infrastructure (Render workspace, logging, storage) complies with relevant regulations and enable available privacy controls in your OpenAI account.
