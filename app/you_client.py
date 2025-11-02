import os
from collections.abc import Mapping, Sequence
from typing import Optional

import httpx

YDC_AGENTS_URL = "https://api.you.com/v1/agents/runs"


def _extract_text(data: object) -> str:
    fragments: list[str] = []
    skip_keys = {"type", "role", "id", "name", "agent"}

    def visit(node: object) -> None:
        if node is None:
            return
        if isinstance(node, str):
            fragments.append(node)
            return
        if isinstance(node, Mapping):
            for key, value in node.items():
                if key in {"text", "output_text"} and isinstance(value, str):
                    fragments.append(value)
                elif key not in skip_keys:
                    visit(value)
            return
        if isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for item in node:
                visit(item)

    visit(data)
    return "".join(fragments).strip()


class YouClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("YOU_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing YOU_API_KEY")
        self._transport = transport

    async def run_agent(self, agent: str, content: str, stream: bool = False):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        def structured_payload() -> dict[str, object]:
            base: dict[str, object] = {
                "agent": agent,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": content,
                            }
                        ],
                    }
                ],
            }
            if stream:
                base["stream"] = True
            return base

        def plain_payload() -> dict[str, object]:
            base: dict[str, object] = {
                "agent": agent,
                "input": [
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
            }
            if stream:
                base["stream"] = True
            return base

        async def post_with_payload(client: httpx.AsyncClient, payload: dict[str, object]):
            resp = await client.post(YDC_AGENTS_URL, headers=headers, json=payload)
            resp.raise_for_status()
            return resp

        payload_builders = (structured_payload, plain_payload)
        last_error: Optional[httpx.HTTPStatusError] = None

        async with httpx.AsyncClient(timeout=60.0, transport=self._transport) as client:
            if stream:
                headers["Accept"] = "text/event-stream"
                for build_payload in payload_builders:
                    try:
                        payload = build_payload()
                        resp = await post_with_payload(client, payload)
                        return resp
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code != 422:
                            raise
                        last_error = exc

                detail = last_error.response.text if last_error and last_error.response else ""
                raise RuntimeError(f"You.com API error 422: {detail}")

            for build_payload in payload_builders:
                try:
                    payload = build_payload()
                    resp = await post_with_payload(client, payload)
                    data = resp.json()
                    break
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code != 422:
                        raise
                    last_error = exc
            else:  # pragma: no cover - defensive
                detail = last_error.response.text if last_error and last_error.response else ""
                raise RuntimeError(f"You.com API error 422: {detail}")

        text = ""
        if isinstance(data, dict):
            candidates = [
                data.get("output"),
                data.get("response"),
                data.get("output_text"),
                data.get("data"),
            ]
            for candidate in candidates:
                text = _extract_text(candidate)
                if text:
                    break

        if not text:
            text = _extract_text(data)

        return text
