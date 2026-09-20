"""
مزوّد متوافق مع صيغة OpenAI Chat Completions API — يشتغل مع OpenAI نفسه
وأي مزوّد يوفر نفس الصيغة (DeepSeek مثلًا)
"""
import json
from collections.abc import AsyncIterator

import httpx

from app.services.ai_providers.base import AIProvider, AIReply


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _messages(
        self, message: str, history: list[dict[str, str]] | None
    ) -> list[dict[str, str]]:
        return (history or []) + [{"role": "user", "content": message}]

    async def get_reply(self, message: str, history: list[dict[str, str]] | None = None) -> AIReply:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={"model": self.model, "messages": self._messages(message, history)},
            )
            response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        return AIReply(
            text=data["choices"][0]["message"]["content"],
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    async def stream_reply(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": self._messages(message, history),
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[len("data: ") :]
                    if data.strip() == "[DONE]":
                        break
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content")
                    if delta:
                        yield delta
