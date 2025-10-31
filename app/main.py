import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.prompts import SUMMARIZE_SYSTEM, TRIAGE_SYSTEM
from app.schemas import ModeRequest, SummarizeResponse, TriageResponse
from app.you_client import YouClient

AGENT_ID_SUMMARIZE = os.getenv("YOU_AGENT_SUMMARIZE_ID", "express")
AGENT_ID_TRIAGE = os.getenv("YOU_AGENT_TRIAGE_ID", "express")

app = FastAPI(title="Clinician Helper")
templates = Jinja2Templates(directory="app/templates")
you_client = YouClient()


@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    response = await call_next(request)
    # Forcefully disable caching at every layer so redeploys immediately reflect UI changes.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/summarize", response_model=SummarizeResponse)
async def summarize(req: ModeRequest):
    stream = bool(req.stream)
    content = f"{SUMMARIZE_SYSTEM}\n\n---\nNOTES:\n{req.text}"

    try:
        if stream:
            response = await you_client.run_agent(AGENT_ID_SUMMARIZE, content, stream=True)
            return StreamingResponse(response.aiter_text(), media_type="text/event-stream")

        text = await you_client.run_agent(AGENT_ID_SUMMARIZE, content, stream=False)
        if not text:
            raise HTTPException(status_code=502, detail="Empty response from LLM")
        return SummarizeResponse(summary=text)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - external service errors
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/triage", response_model=TriageResponse)
async def triage(req: ModeRequest):
    stream = bool(req.stream)
    content = (
        f"{TRIAGE_SYSTEM}\n\n---\nCALL NOTES:\n{req.text}\n\n"
        "Output as a numbered list."
    )

    try:
        if stream:
            response = await you_client.run_agent(AGENT_ID_TRIAGE, content, stream=True)
            return StreamingResponse(response.aiter_text(), media_type="text/event-stream")

        text = await you_client.run_agent(AGENT_ID_TRIAGE, content, stream=False)
        if not text:
            raise HTTPException(status_code=502, detail="Empty response from LLM")

        questions = [line.strip(" -") for line in text.splitlines() if line.strip()]
        return TriageResponse(questions=questions or [text])
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - external service errors
        raise HTTPException(status_code=500, detail=str(exc))
