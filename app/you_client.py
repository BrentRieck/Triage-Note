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
        response_mode: dict[str, object] = {
            "type": "streaming" if stream else "blocking",
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
                "response_mode": response_mode,
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
                "response_mode": response_mode,
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

        def append_text(acc: list[str], value: object) -> None:
            if isinstance(value, str):
                acc.append(value)
            elif isinstance(value, dict):
                if isinstance(value.get("text"), str):
                    acc.append(str(value["text"]))

                # Nested output_text arrays from You.com custom agent API
                if isinstance(value.get("output_text"), list):
                    for item in value["output_text"]:
                        append_text(acc, item)

                # Generic content key can be a string, dict, or list.
                if "content" in value:
                    append_text(acc, value["content"])

                # Some responses are nested under a "run" or "output" object.
                for key in ("output", "run", "response"):
                    if key in value:
                        append_text(acc, value[key])
            elif isinstance(value, list):
                for item in value:
                    append_text(acc, item)

        text_parts: list[str] = []
        append_text(text_parts, data)

        return "".join(part for part in text_parts if isinstance(part, str)).strip()
