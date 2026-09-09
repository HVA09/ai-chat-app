"""
مزوّد Anthropic (Claude) — صيغة مختلفة عن OpenAI: header بدل Bearer token،
والرد يجي بصيغة content بدل choices
"""
import json
from collections.abc import AsyncIterator

import httpx

from app.services.ai_providers.base import AIProvider, AIReply

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str, max_tokens: int = 1024):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    def _messages(
        self, message: str, history: list[dict[str, str]] | None
    ) -> list[dict[str, str]]:
        return (history or []) + [{"role": "user", "content": message}]

    async def get_reply(self, message: str, history: list[dict[str, str]] | None = None) -> AIReply:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers=self._headers(),
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "messages": self._messages(message, history),
                },
            )
            response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        return AIReply(
            text=data["content"][0]["text"],
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
        )

    async def stream_reply(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                ANTHROPIC_API_URL,
                headers=self._headers(),
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "messages": self._messages(message, history),
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    event = json.loads(line[len("data: ") :])
                    if event.get("type") == "content_block_delta":
                        text = event.get("delta", {}).get("text")
                        if text:
                            yield text
