import asyncio
import json
import os
from collections.abc import AsyncIterator
from typing import Optional

import httpx

from app.prompts import SUMMARIZE_SYSTEM, TRIAGE_SYSTEM

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIStreamWrapper:
    def __init__(self, response: httpx.Response, client: httpx.AsyncClient) -> None:
        self._response = response
        self._client = client

    def aiter_text(self) -> AsyncIterator[str]:
        async def iterator() -> AsyncIterator[str]:
            try:
                async for line in self._response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line.strip() == "[DONE]":
                        break
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    choices = payload.get("choices", [])
                    for choice in choices:
                        if not isinstance(choice, dict):
                            continue
                        delta = choice.get("delta")
                        if isinstance(delta, dict):
                            content = delta.get("content")
                            if content:
                                yield str(content)
            finally:
                await self._response.aclose()
                await self._client.aclose()

        return iterator()


class OpenAIClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing OPENAI_API_KEY")
        self._transport = transport
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base

    async def run_agent(self, agent: str, content: str, stream: bool = False):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._resolve_model(agent),
            "messages": self._build_messages(agent, content),
            "temperature": 0.0,
        }

        if stream:
            payload["stream"] = True
            headers["Accept"] = "text/event-stream"
            client, response = await self._request_with_retry(
                headers=headers,
                payload=payload,
                expect_stream=True,
            )
            return OpenAIStreamWrapper(response, client)

        data = await self._request_with_retry(
            headers=headers,
            payload=payload,
            expect_stream=False,
        )

        if not isinstance(data, dict):
            raise RuntimeError("Unexpected OpenAI response format")

        text = []
        for choice in data.get("choices", []):
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict):
                content_piece = message.get("content")
                if content_piece:
                    text.append(str(content_piece))

        return "".join(text).strip()

    async def _request_with_retry(
        self,
        *,
        headers: dict[str, str],
        payload: dict,
        expect_stream: bool,
    ):
        attempts = 0
        last_error: Exception | None = None
        while attempts <= self._max_retries:
            attempts += 1
            client = httpx.AsyncClient(timeout=self._timeout, transport=self._transport)
            try:
                response = await client.post(
                    OPENAI_CHAT_COMPLETIONS_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                if expect_stream:
                    return client, response
                data = response.json()
                await client.aclose()
                return data
            except httpx.HTTPStatusError as exc:
                await client.aclose()
                last_error = exc
                status_code = exc.response.status_code
                if not self._should_retry(status_code) or attempts > self._max_retries:
                    raise RuntimeError(self._format_error(status_code)) from exc
                await self._sleep(self._retry_delay(exc.response.headers.get("Retry-After"), attempts))
            except httpx.RequestError as exc:
                await client.aclose()
                last_error = exc
                if attempts > self._max_retries:
                    raise RuntimeError("Failed to reach OpenAI API") from exc
                await self._sleep(self._retry_delay(None, attempts))
            except Exception:
                await client.aclose()
                raise

        if last_error:
            raise RuntimeError("Failed to contact OpenAI API") from last_error
        raise RuntimeError("Failed to contact OpenAI API")

    def _should_retry(self, status_code: int) -> bool:
        return status_code == 429 or 500 <= status_code < 600

    def _retry_delay(self, retry_after: Optional[str], attempts: int) -> float:
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
        return self._backoff_base * (2 ** (attempts - 1))

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    def _format_error(self, status_code: int) -> str:
        if status_code == 429:
            return "OpenAI API rate limit exceeded. Please try again shortly."
        if 500 <= status_code < 600:
            return "OpenAI API is currently unavailable. Please retry later."
        return "Unexpected OpenAI API error."

    def _resolve_model(self, agent: str) -> str:
        agent_key = agent.lower()
        if agent_key == "summarize":
            return os.getenv("OPENAI_MODEL_SUMMARIZE", "gpt-4")
        if agent_key == "triage":
            return os.getenv("OPENAI_MODEL_TRIAGE", "gpt-4")
        return os.getenv("OPENAI_MODEL_DEFAULT", "gpt-4")

    def _build_messages(self, agent: str, user_content: str):
        agent_key = agent.lower()
        if agent_key == "summarize":
            system_prompt = SUMMARIZE_SYSTEM
        elif agent_key == "triage":
            system_prompt = TRIAGE_SYSTEM
        else:
            system_prompt = "You are a helpful clinical assistant."
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
