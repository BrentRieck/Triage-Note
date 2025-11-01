import pytest
import httpx

from app.main import app, get_you_client


class StubYouClient:
    def __init__(self, response: str):
        self.response = response

    async def run_agent(self, agent: str, content: str, stream: bool = False):
        return self.response


@pytest.mark.asyncio
async def test_summarize_returns_summary():
    stub = StubYouClient(response="Summarized text")
    app.dependency_overrides[get_you_client] = lambda: stub

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/summarize", json={"text": "notes", "stream": False})

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == {"summary": "Summarized text"}


@pytest.mark.asyncio
async def test_summarize_returns_502_on_empty_response():
    stub = StubYouClient(response="")
    app.dependency_overrides[get_you_client] = lambda: stub

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/summarize", json={"text": "notes", "stream": False})

    app.dependency_overrides.clear()

    assert resp.status_code == 502
    assert resp.json()["detail"] == "Empty response from LLM"


@pytest.mark.asyncio
async def test_triage_splits_lines_into_questions():
    stub = StubYouClient(response="1. Question one\n2. Question two\n")
    app.dependency_overrides[get_you_client] = lambda: stub

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/triage", json={"text": "notes", "stream": False})

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == {
        "questions": ["1. Question one", "2. Question two"],
    }
