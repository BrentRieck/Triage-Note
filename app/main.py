from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.schemas import ModeRequest, SummarizeResponse, TriageResponse
from app.openai_client import OpenAIClient

app = FastAPI(title="Clinician Helper")
templates = Jinja2Templates(directory="app/templates")


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAIClient:
    return OpenAIClient()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/summarize", response_model=SummarizeResponse)
async def summarize(
    req: ModeRequest, openai_client: OpenAIClient = Depends(get_openai_client)
):
    stream = bool(req.stream)
    user_content = req.text

    try:
        if stream:
            response = await openai_client.run_agent("summarize", user_content, stream=True)
            return StreamingResponse(response.aiter_text(), media_type="text/event-stream")

        text = await openai_client.run_agent("summarize", user_content, stream=False)
        if not text:
            raise HTTPException(status_code=502, detail="Empty response from LLM")
        return SummarizeResponse(summary=text)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - external service errors
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/triage", response_model=TriageResponse)
async def triage(
    req: ModeRequest, openai_client: OpenAIClient = Depends(get_openai_client)
):
    stream = bool(req.stream)
    user_content = f"{req.text}\n\nOutput as a numbered list."

    try:
        if stream:
            response = await openai_client.run_agent("triage", user_content, stream=True)
            return StreamingResponse(response.aiter_text(), media_type="text/event-stream")

        text = await openai_client.run_agent("triage", user_content, stream=False)
        if not text:
            raise HTTPException(status_code=502, detail="Empty response from LLM")

        questions = [line.strip(" -") for line in text.splitlines() if line.strip()]
        return TriageResponse(questions=questions or [text])
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - external service errors
        raise HTTPException(status_code=500, detail=str(exc))
