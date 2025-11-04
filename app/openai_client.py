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
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing OPENAI_API_KEY")
        self._transport = transport
        self._timeout = timeout

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
            client = httpx.AsyncClient(timeout=self._timeout, transport=self._transport)
            try:
                payload["stream"] = True
                headers["Accept"] = "text/event-stream"
                response = await client.post(
                    OPENAI_CHAT_COMPLETIONS_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                return OpenAIStreamWrapper(response, client)
            except Exception:
                await client.aclose()
                raise

        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

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
