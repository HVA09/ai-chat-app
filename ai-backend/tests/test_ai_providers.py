"""
اختبارات المرحلة الخامسة: اختيار مزوّد الـ AI، والبث التدريجي (streaming)
"""
import pytest

from app.config import settings as app_settings
from app.routers import chat as chat_router_module
from app.services.ai_providers.anthropic_provider import AnthropicProvider
from app.services.ai_providers.factory import get_provider
from app.services.ai_providers.gemini_provider import GeminiProvider
from app.services.ai_providers.openai_provider import OpenAICompatibleProvider


def _register_and_login(client, email="stream@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.json()["access_token"]


def test_factory_defaults_to_openai_provider():
    provider = get_provider()
    assert isinstance(provider, OpenAICompatibleProvider)


def test_factory_deepseek_uses_openai_compatible_provider(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "deepseek")
    provider = get_provider()
    assert isinstance(provider, OpenAICompatibleProvider)


def test_factory_returns_anthropic_provider(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "anthropic")
    provider = get_provider()
    assert isinstance(provider, AnthropicProvider)


def test_factory_returns_gemini_provider(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "gemini")
    provider = get_provider()
    assert isinstance(provider, GeminiProvider)


def test_factory_rejects_unsupported_provider(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "not_a_real_provider")
    with pytest.raises(ValueError):
        get_provider()


def test_gemini_maps_assistant_role_to_model():
    provider = GeminiProvider(api_key="fake", model="gemini-1.5-flash")
    history = [
        {"role": "user", "content": "مرحبا"},
        {"role": "assistant", "content": "أهلًا بك"},
    ]
    contents = provider._contents("كيف حالك", history)

    assert contents[0]["role"] == "user"
    assert contents[1]["role"] == "model"  # مو "assistant" — صيغة Gemini مختلفة
    assert contents[2]["role"] == "user"
    assert contents[2]["parts"][0]["text"] == "كيف حالك"


def test_stream_chat_returns_sse_events(client, monkeypatch):
    async def fake_stream(message, history=None):
        for chunk in ["مرحبا", " بك"]:
            yield chunk

    monkeypatch.setattr(chat_router_module, "stream_ai_reply", fake_stream)

    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    with client.stream(
        "POST", "/chat/stream", json={"message": "أهلا"}, headers=headers
    ) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())

    assert "event: conversation" in body
    assert "event: chunk" in body
    assert "مرحبا" in body
    assert "event: done" in body


def test_stream_chat_requires_authentication(client):
    with client.stream("POST", "/chat/stream", json={"message": "أهلا"}) as response:
        assert response.status_code == 401
