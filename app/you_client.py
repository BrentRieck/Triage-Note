import os
from typing import Optional

import httpx

YDC_AGENTS_URL = "https://api.you.com/v1/agents/runs"


class YouClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("YOU_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing YOU_API_KEY")

    async def run_agent(self, agent: str, content: str, stream: bool = False):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, object] = {"agent": agent, "input": content}
        if stream:
            payload["stream"] = True

        async with httpx.AsyncClient(timeout=60.0) as client:
            if stream:
                headers["Accept"] = "text/event-stream"
                resp = await client.post(YDC_AGENTS_URL, headers=headers, json=payload)
                resp.raise_for_status()
                return resp

            resp = await client.post(YDC_AGENTS_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = ""
        if isinstance(data, dict) and data.get("output"):
            for item in data["output"]:
                if isinstance(item, dict) and item.get("text"):
                    text += item["text"]
        return text.strip()
