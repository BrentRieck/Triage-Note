# Clinician Helper

FastAPI web application that helps healthcare professionals summarize clinical notes, draft telephone triage question lists, and compose patient-friendly replies using the You.com Agents API.

## Features

- **Summarize Notes:** Convert messy, unstructured clinical notes into concise professional documentation.
- **Triage Questions:** Turn patient call transcripts into prioritized triage question checklists.
- **Patient Replies:** Generate empathetic, clinically appropriate responses clinicians can send back to patients.
- Minimal HTML UI for quick testing and REST API endpoints for integration.

## Prerequisites

- Python 3.11+
- You.com Agents API key (`YOU_API_KEY`).
- Optional: You.com custom agent IDs for summarization, triage, and patient reply modes.

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export YOU_API_KEY=your_you_com_key
# Optional if you created custom agents in You.com UI
export YOU_AGENT_SUMMARIZE_ID=agent_id_for_summaries
export YOU_AGENT_TRIAGE_ID=agent_id_for_triage
export YOU_AGENT_REPLY_ID=agent_id_for_replies
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000 to use the UI.

## API Endpoints

- `POST /api/summarize` → `{ "text": "..." }` → `{ "summary": "..." }`
- `POST /api/triage` → `{ "text": "..." }` → `{ "questions": ["..."] }`
- `POST /api/reply` → `{ "text": "..." }` → `{ "reply": "..." }`

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

- `YOU_API_KEY`
- `YOU_AGENT_SUMMARIZE_ID` (optional)
- `YOU_AGENT_TRIAGE_ID` (optional)
- `YOU_AGENT_REPLY_ID` (optional)

For environments subject to HIPAA or similar requirements, deploy into a HIPAA-enabled Render workspace and enable privacy protections within You.com (e.g., Zero Data Retention) as needed.

## Creating You.com Agents (Recommended)

1. In the You.com UI, create three custom agents:
   - **Clinical Note Summarizer** – use the instructions from `SUMMARIZE_SYSTEM`.
   - **Telephone Triage Question Builder** – use the instructions from `TRIAGE_SYSTEM`.
   - **Patient Message Reply Assistant** – use the instructions from `REPLY_SYSTEM`.
2. Grab each agent's ID and configure the `YOU_AGENT_SUMMARIZE_ID`, `YOU_AGENT_TRIAGE_ID`, and `YOU_AGENT_REPLY_ID` environment variables.
3. The app falls back to the Express agent with inline instructions if agent IDs are not supplied.

## Security Notes

- Never commit API keys. Use environment variables locally and in deployment.
- If handling PHI, ensure the infrastructure (Render workspace, logging, storage) complies with relevant regulations and enable available privacy controls in You.com.
