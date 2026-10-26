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
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_factory_defaults_to_openai_provider():
    provider = get_provider()
    assert isinstance(provider, OpenAICompatibleProvider)


def test_factory_deepseek_uses_openai_compatible_provider(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "deepseek")
    assert isinstance(get_provider(), OpenAICompatibleProvider)


def test_factory_returns_anthropic_provider(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "anthropic")
    assert isinstance(get_provider(), AnthropicProvider)


def test_factory_gemini_uses_openai_compatible_provider(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(app_settings, "AI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    monkeypatch.setattr(app_settings, "AI_MODEL", "gemini-2.5-flash")
    provider = get_provider()
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert provider.model == "gemini-2.5-flash"


def test_factory_rejects_unsupported_provider(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "not_a_real_provider")
    with pytest.raises(ValueError):
        get_provider()


def test_gemini_maps_assistant_role_to_model():
    provider = GeminiProvider(api_key="fake", model="gemini-1.5-flash")
    history = [{"role": "user", "content": "مرحبا"}, {"role": "assistant", "content": "أهلًا بك"}]
    contents = provider._contents("كيف حالك", history)
    assert contents[0]["role"] == "user"
    assert contents[1]["role"] == "model"
    assert contents[2]["role"] == "user"
    assert contents[2]["parts"][0]["text"] == "كيف حالك"


def test_stream_chat_returns_sse_events(client, monkeypatch):
    async def fake_stream(message, history=None, model=None, on_provider_selected=None):
        if on_provider_selected is not None:
            on_provider_selected("gemini")
        for chunk in ["مرحبا", " بك"]:
            yield chunk
    monkeypatch.setattr(chat_router_module, "stream_ai_reply", fake_stream)
    token = _register_and_login(client)
    with client.stream("POST", "/chat/stream", json={"message": "أهلا"}, headers={"Authorization": f"Bearer {token}"}) as response:
        assert response.status_code == 200
        body = "".join(response.iter_text())
    assert "event: conversation" in body
    assert "event: chunk" in body
    assert "مرحبا" in body
    assert "event: done" in body


def test_stream_chat_requires_authentication(client):
    with client.stream("POST", "/chat/stream", json={"message": "أهلا"}) as response:
        assert response.status_code == 401


def test_factory_accepts_an_allowed_model(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(app_settings, "AI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    monkeypatch.setattr(app_settings, "AI_ALLOWED_MODELS", ["gemini-2.5-flash", "gemini-test"])
    provider = get_provider("gemini-test")
    assert provider.model == "gemini-test"


def test_factory_rejects_disallowed_model(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(app_settings, "AI_ALLOWED_MODELS", ["gemini-2.5-flash"])
    try:
        get_provider("not-allowed")
    except ValueError as exc:
        assert "غير مسموح" in str(exc)
    else:
        raise AssertionError("Expected get_provider to reject a disallowed model")


def test_factory_allows_internal_fallback_model_override(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(app_settings, "AI_API_KEY", "primary-key")
    monkeypatch.setattr(app_settings, "AI_API_BASE_URL", "https://primary.example/v1")
    monkeypatch.setattr(app_settings, "AI_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(app_settings, "AI_ALLOWED_MODELS", ["gemini-2.5-flash"])

    provider = get_provider(
        model="claude-test",
        provider_name="anthropic",
        api_key="fallback-key",
        validate_model=False,
    )

    assert provider.api_key == "fallback-key"
    assert provider.model == "claude-test"


def test_factory_supports_explicit_provider_override(monkeypatch):
    monkeypatch.setattr(app_settings, "AI_PROVIDER", "gemini")
    monkeypatch.setattr(app_settings, "AI_API_KEY", "primary-key")
    monkeypatch.setattr(app_settings, "AI_API_BASE_URL", "https://primary.example/v1")
    monkeypatch.setattr(app_settings, "AI_MODEL", "gemini-2.5-flash")
    provider = get_provider(
        model="gemini-2.5-flash",
        provider_name="openai",
        api_key="fallback-key",
        base_url="https://fallback.example/v1",
    )
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.api_key == "fallback-key"
    assert provider.base_url == "https://fallback.example/v1"


def test_non_stream_ai_request_uses_configured_timeout(monkeypatch):
    import asyncio
    import httpx

    monkeypatch.setattr(app_settings, "AI_REQUEST_TIMEOUT_SECONDS", 17.0)
    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "رد"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            seen["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    reply = asyncio.run(
        OpenAICompatibleProvider(
            api_key="fake",
            base_url="https://example.com/v1",
            model="test-model",
        ).get_reply("hello")
    )

    assert reply.text == "رد"
    assert seen["timeout"] == 17.0


def _install_fake_provider_client(monkeypatch, provider_module, response_data):
    """Capture outgoing provider payloads without making network requests."""
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return response_data

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *args, **kwargs):
            captured["url"] = url
            captured["payload"] = kwargs.get("json")
            return FakeResponse()

    monkeypatch.setattr(provider_module.httpx, "AsyncClient", FakeClient)
    return captured


def test_openai_compatible_provider_sends_system_prompt_before_user_history(monkeypatch):
    import asyncio
    from app.services.ai_providers import openai_provider
    from app.services.ai_providers.instructions import SYSTEM_PROMPT

    captured = _install_fake_provider_client(
        monkeypatch,
        openai_provider,
        {
            "choices": [{"message": {"content": "reply"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        },
    )
    provider = OpenAICompatibleProvider(
        api_key="fake",
        base_url="https://example.com/v1",
        model="test-model",
    )
    history = [
        {"role": "system", "content": "Task-specific system guidance."},
        {"role": "user", "content": "Earlier message"},
    ]

    reply = asyncio.run(provider.get_reply("Current question", history))

    messages = captured["payload"]["messages"]
    assert reply.text == "reply"
    assert messages[0]["role"] == "system"
    assert SYSTEM_PROMPT in messages[0]["content"]
    assert "Task-specific system guidance." in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "Current question"}
    assert history[0]["content"] == "Task-specific system guidance."


def test_openai_compatible_vision_request_includes_system_prompt(monkeypatch):
    import asyncio
    from app.services.ai_providers import openai_provider
    from app.services.ai_providers.instructions import SYSTEM_PROMPT

    captured = _install_fake_provider_client(
        monkeypatch,
        openai_provider,
        {
            "choices": [{"message": {"content": "image summary"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        },
    )
    provider = OpenAICompatibleProvider(
        api_key="fake",
        base_url="https://example.com/v1",
        model="vision-model",
    )

    reply = asyncio.run(
        provider.get_vision_reply(
            "Describe this image",
            "data:image/png;base64,ZmFrZQ==",
        )
    )

    messages = captured["payload"]["messages"]
    assert reply.text == "image summary"
    assert messages[0]["role"] == "system"
    assert SYSTEM_PROMPT in messages[0]["content"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"][1]["type"] == "image_url"


def test_openai_tool_request_preserves_system_level_guardrails(monkeypatch):
    import asyncio
    from app.services.ai_providers import openai_provider
    from app.services.ai_providers.instructions import SYSTEM_PROMPT

    captured = _install_fake_provider_client(
        monkeypatch,
        openai_provider,
        {
            "choices": [{"message": {"content": "done", "tool_calls": []}}],
            "usage": {},
        },
    )
    provider = OpenAICompatibleProvider(
        api_key="fake",
        base_url="https://example.com/v1",
        model="tool-model",
    )

    asyncio.run(
        provider.get_reply_with_tools(
            messages=[
                {"role": "system", "content": "Use the calculator for arithmetic."},
                {"role": "user", "content": "What is 2+2?"},
            ],
            tools=[],
            tool_choice="none",
        )
    )

    first_message = captured["payload"]["messages"][0]
    assert first_message["role"] == "system"
    assert SYSTEM_PROMPT in first_message["content"]
    assert "Use the calculator for arithmetic." in first_message["content"]


def test_anthropic_provider_uses_native_system_field(monkeypatch):
    import asyncio
    from app.services.ai_providers import anthropic_provider
    from app.services.ai_providers.instructions import SYSTEM_PROMPT

    captured = _install_fake_provider_client(
        monkeypatch,
        anthropic_provider,
        {"content": [{"text": "reply"}], "usage": {"input_tokens": 1, "output_tokens": 1}},
    )
    provider = AnthropicProvider(api_key="fake", model="claude-test")
    history = [
        {"role": "system", "content": "Narrow task instructions."},
        {"role": "user", "content": "Earlier message"},
    ]

    reply = asyncio.run(provider.get_reply("Current question", history))

    assert reply.text == "reply"
    assert SYSTEM_PROMPT in captured["payload"]["system"]
    assert "Narrow task instructions." in captured["payload"]["system"]
    assert all(message["role"] != "system" for message in captured["payload"]["messages"])
    assert captured["payload"]["messages"][-1]["content"] == "Current question"


def test_gemini_provider_uses_native_system_instruction_field(monkeypatch):
    import asyncio
    from app.services.ai_providers import gemini_provider
    from app.services.ai_providers.instructions import SYSTEM_PROMPT

    captured = _install_fake_provider_client(
        monkeypatch,
        gemini_provider,
        {
            "candidates": [{"content": {"parts": [{"text": "reply"}]}}],
            "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1},
        },
    )
    provider = GeminiProvider(api_key="fake", model="gemini-test")
    history = [
        {"role": "system", "content": "Narrow task instructions."},
        {"role": "assistant", "content": "Earlier assistant reply"},
    ]

    reply = asyncio.run(provider.get_reply("Current question", history))

    system_text = captured["payload"]["systemInstruction"]["parts"][0]["text"]
    assert reply.text == "reply"
    assert SYSTEM_PROMPT in system_text
    assert "Narrow task instructions." in system_text
    assert all(item["role"] != "system" for item in captured["payload"]["contents"])
    assert captured["payload"]["contents"][-1] == {
        "role": "user",
        "parts": [{"text": "Current question"}],
    }


def _install_fake_stream_provider_client(monkeypatch, provider_module, lines):
    """Capture streaming API requests and return deterministic SSE lines."""
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        async def aiter_lines(self):
            for line in lines:
                yield line

    class FakeStreamContext:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def stream(self, method, url, *args, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["payload"] = kwargs.get("json")
            return FakeStreamContext()

    monkeypatch.setattr(provider_module.httpx, "AsyncClient", FakeClient)
    return captured


def test_openai_compatible_stream_includes_system_guardrails(monkeypatch):
    import asyncio
    from app.services.ai_providers import openai_provider
    from app.services.ai_providers.instructions import SYSTEM_PROMPT

    captured = _install_fake_stream_provider_client(
        monkeypatch,
        openai_provider,
        [
            'data: {"choices":[{"delta":{"content":"streamed"}}]}',
            "data: [DONE]",
        ],
    )
    provider = OpenAICompatibleProvider(
        api_key="fake",
        base_url="https://example.com/v1",
        model="test-model",
    )
    history = [
        {"role": "system", "content": "Task-specific stream guidance."},
        {"role": "user", "content": "Earlier message"},
    ]

    async def collect():
        return [
            part
            async for part in provider.stream_reply("Current question", history)
        ]

    assert asyncio.run(collect()) == ["streamed"]
    messages = captured["payload"]["messages"]
    assert messages[0]["role"] == "system"
    assert SYSTEM_PROMPT in messages[0]["content"]
    assert "Task-specific stream guidance." in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "Current question"}
    assert captured["payload"]["stream"] is True


def test_anthropic_stream_uses_native_system_guardrails(monkeypatch):
    import asyncio
    from app.services.ai_providers import anthropic_provider
    from app.services.ai_providers.instructions import SYSTEM_PROMPT

    captured = _install_fake_stream_provider_client(
        monkeypatch,
        anthropic_provider,
        [
            'data: {"type":"content_block_delta","delta":{"text":"streamed"}}',
            'data: {"type":"message_stop"}',
        ],
    )
    provider = AnthropicProvider(api_key="fake", model="claude-test")
    history = [
        {"role": "system", "content": "Task-specific stream guidance."},
        {"role": "assistant", "content": "Earlier assistant reply"},
    ]

    async def collect():
        return [
            part
            async for part in provider.stream_reply("Current question", history)
        ]

    assert asyncio.run(collect()) == ["streamed"]
    assert SYSTEM_PROMPT in captured["payload"]["system"]
    assert "Task-specific stream guidance." in captured["payload"]["system"]
    assert all(item["role"] != "system" for item in captured["payload"]["messages"])
    assert captured["payload"]["stream"] is True


def test_gemini_stream_uses_native_system_instruction_guardrails(monkeypatch):
    import asyncio
    from app.services.ai_providers import gemini_provider
    from app.services.ai_providers.instructions import SYSTEM_PROMPT

    captured = _install_fake_stream_provider_client(
        monkeypatch,
        gemini_provider,
        [
            'data: {"candidates":[{"content":{"parts":[{"text":"streamed"}]}}]}',
        ],
    )
    provider = GeminiProvider(api_key="fake", model="gemini-test")
    history = [
        {"role": "system", "content": "Task-specific stream guidance."},
        {"role": "assistant", "content": "Earlier assistant reply"},
    ]

    async def collect():
        return [
            part
            async for part in provider.stream_reply("Current question", history)
        ]

    assert asyncio.run(collect()) == ["streamed"]
    system_text = captured["payload"]["systemInstruction"]["parts"][0]["text"]
    assert SYSTEM_PROMPT in system_text
    assert "Task-specific stream guidance." in system_text
    assert all(item["role"] != "system" for item in captured["payload"]["contents"])
    assert captured["payload"]["contents"][-1] == {
        "role": "user",
        "parts": [{"text": "Current question"}],
    }
