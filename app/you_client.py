import os
from typing import Optional

import httpx

YDC_AGENTS_URL = "https://api-you.com/v1/agents/runs"


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
        if isinstance(data, dict) and data.get("output"):
            for item in data["output"]:
                if isinstance(item, str):
                    text += item
                    continue

                if isinstance(item, dict):
                    if item.get("text"):
                        text += str(item["text"])
                        continue

                    contents = item.get("content")
                    if isinstance(contents, str):
                        text += contents
                        continue

                    if isinstance(contents, list):
                        for piece in contents:
                            if (
                                isinstance(piece, dict)
                                and piece.get("text")
                                and piece.get("type") in {"output_text", "input_text", "text"}
                            ):
                                text += str(piece["text"])
        return text.strip()
