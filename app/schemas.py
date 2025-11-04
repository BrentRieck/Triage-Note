from typing import Optional

from pydantic import BaseModel, Field


class ModeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    stream: Optional[bool] = False  # enable SSE if desired


class SummarizeResponse(BaseModel):
    summary: str


class TriageResponse(BaseModel):
    questions: list[str]


class ReplyResponse(BaseModel):
    reply: str
