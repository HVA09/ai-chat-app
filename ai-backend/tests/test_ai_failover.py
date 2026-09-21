"""اختبارات التحويل الاحتياطي بين مزوّدي الذكاء الاصطناعي."""
import asyncio

import httpx
import pytest

from app.config import settings as app_settings
from app.services import ai_service
from app.services.ai_providers.base import AIReply


class FakeProvider:
    def __init__(self, reply=None, error=None, chunks=None):
        self.reply = reply
        self.error = error
        self.chunks = chunks or []

    async def get_reply(self, message, history=None):
        if self.error:
            raise self.error
        return self.reply

    async def stream_reply(self, message, history=None):
        if self.error:
            raise self.error
        for chunk in self.chunks:
            yield chunk


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("provider error", request=request, response=response)


def test_get_ai_reply_uses_fallback_on_rate_limit(monkeypatch):
    calls = []

    primary = FakeProvider(error=_http_error(429))
    fallback = FakeProvider(reply=AIReply(text="fallback", input_tokens=1, output_tokens=2))

    def fake_get_provider(model=None, provider_name=None, api_key=None, base_url=None):
        calls.append((model, provider_name))
        return fallback if provider_name == "anthropic" else primary

    monkeypatch.setattr(ai_service, "get_provider", fake_get_provider)
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(app_settings, "AI_API_KEY", "primary")
    monkeypatch.setattr(app_settings, "AI_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(app_settings, "AI_FALLBACK_PROVIDER", "anthropic")
    monkeypatch.setattr(app_settings, "AI_FALLBACK_API_KEY", "fallback")
    monkeypatch.setattr(app_settings, "AI_FALLBACK_MODEL", "claude-test")
    monkeypatch.setattr(app_settings, "AI_ALLOWED_MODELS", ["gemini-2.5-flash"])

    result = asyncio.run(ai_service.get_ai_reply("hello"))

    assert result.text == "fallback"
    assert calls == [(None, None), ("claude-test", "anthropic")]


def test_get_ai_reply_does_not_failover_on_auth_error(monkeypatch):
    primary = FakeProvider(error=_http_error(401))
    fallback = FakeProvider(reply=AIReply(text="fallback"))

    def fake_get_provider(model=None, provider_name=None, api_key=None, base_url=None):
        return fallback if provider_name == "anthropic" else primary

    monkeypatch.setattr(ai_service, "get_provider", fake_get_provider)
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(app_settings, "AI_API_KEY", "primary")
    monkeypatch.setattr(app_settings, "AI_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(app_settings, "AI_FALLBACK_PROVIDER", "anthropic")
    monkeypatch.setattr(app_settings, "AI_FALLBACK_API_KEY", "fallback")

    with pytest.raises(Exception) as exc:
        asyncio.run(ai_service.get_ai_reply("hello"))

    assert getattr(exc.value, "status_code", None) == 502


def test_stream_ai_reply_fails_over_before_first_chunk(monkeypatch):
    primary = FakeProvider(error=_http_error(503))
    fallback = FakeProvider(chunks=["A", "B"])

    def fake_get_provider(model=None, provider_name=None, api_key=None, base_url=None):
        return fallback if provider_name == "anthropic" else primary

    monkeypatch.setattr(ai_service, "get_provider", fake_get_provider)
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(app_settings, "AI_API_KEY", "primary")
    monkeypatch.setattr(app_settings, "AI_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(app_settings, "AI_FALLBACK_PROVIDER", "anthropic")
    monkeypatch.setattr(app_settings, "AI_FALLBACK_API_KEY", "fallback")
    monkeypatch.setattr(app_settings, "AI_FALLBACK_MODEL", "claude-test")
    monkeypatch.setattr(app_settings, "AI_ALLOWED_MODELS", ["gemini-2.5-flash"])

    async def collect():
        return [chunk async for chunk in ai_service.stream_ai_reply("hello")]

    chunks = asyncio.run(collect())

    assert chunks == ["A", "B"]


def test_stream_ai_reply_does_not_switch_after_partial_output(monkeypatch):
    primary = FakeProvider(chunks=["A"])
    fallback = FakeProvider(chunks=["B"])

    async def broken_stream(message, history=None):
        yield "A"
        raise _http_error(503)

    primary.stream_reply = broken_stream

    def fake_get_provider(*, model=None, provider_name=None, api_key=None, base_url=None):
        return fallback if provider_name == "anthropic" else primary

    monkeypatch.setattr(ai_service, "get_provider", fake_get_provider)
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(app_settings, "AI_FALLBACK_PROVIDER", "anthropic")
    monkeypatch.setattr(app_settings, "AI_FALLBACK_API_KEY", "fallback")

    async def collect():
        chunks = []
        try:
            async for chunk in ai_service.stream_ai_reply("hello"):
                chunks.append(chunk)
        except httpx.HTTPStatusError:
            pass
        return chunks

    chunks = asyncio.run(collect())

    assert chunks == ["A"]
