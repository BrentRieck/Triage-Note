import os

from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.prompts import SUMMARIZE_SYSTEM, TRIAGE_SYSTEM
from app.schemas import ModeRequest, SummarizeResponse, TriageResponse
from app.user_schemas import UserCreate, UserRead, UserUpdate
from app.you_client import YouClient
from app.auth import auth_backend, current_active_user, fastapi_users
from app.models import User

AGENT_ID_SUMMARIZE = os.getenv("YOU_AGENT_SUMMARIZE_ID", "express")
AGENT_ID_TRIAGE = os.getenv("YOU_AGENT_TRIAGE_ID", "express")

app = FastAPI(title="Clinician Helper")
templates = Jinja2Templates(directory="app/templates")


app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"]
)


@lru_cache(maxsize=1)
def get_you_client() -> YouClient:
    return YouClient()


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request, current_user: User = Depends(current_active_user)
):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/summarize", response_model=SummarizeResponse)
async def summarize(
    req: ModeRequest,
    you_client: YouClient = Depends(get_you_client),
    current_user: User = Depends(current_active_user),
):
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
async def triage(
    req: ModeRequest,
    you_client: YouClient = Depends(get_you_client),
    current_user: User = Depends(current_active_user),
):
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
