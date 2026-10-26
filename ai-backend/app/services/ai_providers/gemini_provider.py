"""
مزوّد Google Gemini — صيغة مختلفة تمامًا: contents/parts، والمفتاح كـ query param،
ودور المساعد اسمه "model" مو "assistant"
"""
import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings
from app.services.ai_providers.base import AIProvider, AIReply
from app.services.ai_providers.instructions import SYSTEM_PROMPT

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def _contents(
        self, message: str, history: list[dict[str, str]] | None
    ) -> list[dict[str, object]]:
        contents = []
        for m in history or []:
            if m.get("role") == "system":
                continue
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        contents.append({"role": "user", "parts": [{"text": message}]})
        return contents

    def _system_instruction(
        self, history: list[dict[str, str]] | None
    ) -> dict[str, list[dict[str, str]]]:
        existing = [
            str(item.get("content") or "")
            for item in (history or [])
            if item.get("role") == "system" and str(item.get("content") or "").strip()
        ]
        text = "\n\n".join([SYSTEM_PROMPT, *existing])
        return {"parts": [{"text": text}]}

    async def get_reply(self, message: str, history: list[dict[str, str]] | None = None) -> AIReply:
        url = f"{GEMINI_BASE_URL}/models/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                json={
                    "systemInstruction": self._system_instruction(history),
                    "contents": self._contents(message, history),
                },
            )
            response.raise_for_status()
        data = response.json()
        usage = data.get("usageMetadata") or {}
        return AIReply(
            text=data["candidates"][0]["content"]["parts"][0]["text"],
            input_tokens=usage.get("promptTokenCount"),
            output_tokens=usage.get("candidatesTokenCount"),
        )

    async def stream_reply(
        self, message: str, history: list[dict[str, str]] | None = None
    ) -> AsyncIterator[str]:
        url = (
            f"{GEMINI_BASE_URL}/models/{self.model}:streamGenerateContent"
            f"?key={self.api_key}&alt=sse"
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                url,
                json={
                    "systemInstruction": self._system_instruction(history),
                    "contents": self._contents(message, history),
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = json.loads(line[len("data: ") :])
                    try:
                        text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                    except (KeyError, IndexError):
                        continue
                    if text:
                        yield text
