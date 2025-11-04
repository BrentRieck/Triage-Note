import json
from collections.abc import AsyncIterator

import httpx
import pytest

from app.openai_client import OPENAI_CHAT_COMPLETIONS_URL, OpenAIClient
from app.prompts import SUMMARIZE_SYSTEM, TRIAGE_SYSTEM


class DummyStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk

    def __aiter__(self) -> AsyncIterator[bytes]:  # pragma: no cover - simple delegation
        return self.aiter_bytes()

    async def aclose(self) -> None:  # pragma: no cover - nothing to close in tests
        return None


@pytest.mark.asyncio
async def test_run_agent_builds_summarize_messages(monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Summarized"}}]},
        )

    transport = httpx.MockTransport(handler)
    client = OpenAIClient(api_key="test", transport=transport)

    result = await client.run_agent("summarize", "Patient notes", stream=False)

    assert result == "Summarized"
    assert captured["url"] == OPENAI_CHAT_COMPLETIONS_URL
    payload = captured["payload"]
    assert payload["model"] == "gpt-4"
    assert payload["messages"][0] == {"role": "system", "content": SUMMARIZE_SYSTEM}
    assert payload["messages"][1] == {"role": "user", "content": "Patient notes"}


@pytest.mark.asyncio
async def test_run_agent_streams_triage_content(monkeypatch: pytest.MonkeyPatch):
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode())
        assert payload["messages"][0]["content"] == TRIAGE_SYSTEM
        stream = DummyStream(
            [
                b'data: {"choices": [{"delta": {"content": "Q1"}}]}\n\n',
                b'data: {"choices": [{"delta": {"content": " and Q2"}}]}\n\n',
                b"data: [DONE]\n\n",
            ]
        )
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            stream=stream,
        )

    transport = httpx.MockTransport(handler)
    client = OpenAIClient(api_key="test", transport=transport)

    response = await client.run_agent("triage", "Call notes", stream=True)

    chunks: list[str] = []
    async for part in response.aiter_text():
        chunks.append(part)

    assert "".join(chunks) == "Q1 and Q2"


def test_client_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        OpenAIClient(api_key=None)
