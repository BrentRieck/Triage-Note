import json

import httpx
import pytest

from app.you_client import YouClient


@pytest.mark.asyncio
async def test_run_agent_falls_back_to_plain_payload():
    calls = {"count": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        payload = json.loads(request.content.decode())

        if calls["count"] == 1:
            # Structured payload is attempted first and rejected.
            assert isinstance(payload["input"], list)
            assert payload["input"][0]["content"][0]["type"] == "input_text"
            return httpx.Response(422, json={"detail": "Invalid structure"})

        # Fallback uses the plain payload with string content.
        assert payload["input"][0]["content"] == "hello"
        return httpx.Response(200, json={"output": [{"text": "Hi"}]})

    transport = httpx.MockTransport(handler)
    client = YouClient(api_key="test", transport=transport)

    result = await client.run_agent("express", "hello", stream=False)

    assert calls["count"] == 2
    assert result == "Hi"


@pytest.mark.asyncio
async def test_run_agent_raises_after_all_payloads_fail():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "Invalid"})

    transport = httpx.MockTransport(handler)
    client = YouClient(api_key="test", transport=transport)

    with pytest.raises(RuntimeError) as exc:
        await client.run_agent("express", "hello", stream=False)

    assert "You.com API error 422" in str(exc.value)


@pytest.mark.asyncio
async def test_run_agent_concatenates_complex_output():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "output": [
                    "Direct text ",
                    {"text": "chunk "},
                    {"content": "string content "},
                    {
                        "content": [
                            {"type": "output_text", "text": "nested "},
                            {"type": "input_text", "text": "pieces"},
                        ]
                    },
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    client = YouClient(api_key="test", transport=transport)

    result = await client.run_agent("express", "hello", stream=False)

    assert result == "Direct text chunk string content nested pieces"


@pytest.mark.asyncio
async def test_run_agent_handles_nested_response_payload():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "response": {
                    "output": [
                        {
                            "content": [
                                {"type": "output_text", "text": "Drafting "},
                                {"type": "output_text", "text": "patient reply"},
                            ]
                        }
                    ]
                }
            },
        )

    transport = httpx.MockTransport(handler)
    client = YouClient(api_key="test", transport=transport)

    result = await client.run_agent("express", "hello", stream=False)

    assert result == "Drafting patient reply"
