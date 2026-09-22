"""اختبارات وضع الوكيل واستدعاء الأدوات الآمنة."""
from app.services.ai_providers.base import AIToolCall, AIToolReply
from app.services.ai_providers.openai_provider import OpenAICompatibleProvider


def _register_and_login(client, email="agent@example.com"):
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


class FakeToolProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(api_key="test", base_url="http://example.test/v1", model="fake")

    async def get_reply_with_tools(self, messages, tools, tool_choice="auto"):
        if any(item.get("role") == "tool" for item in messages):
            return AIToolReply(text="حسبت العملية: الناتج 60.")
        return AIToolReply(
            tool_calls=[
                AIToolCall(
                    id="call-1",
                    name="calculator",
                    arguments={"expression": "(12 + 8) * 3"},
                )
            ]
        )


def test_agent_mode_selects_calculator_and_returns_final_answer(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_agent.get_provider",
        lambda model=None: FakeToolProvider(),
    )
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/chat",
        json={"message": "/agent احسب (12 + 8) * 3"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "حسبت العملية: الناتج 60."
    conversation_id = response.json()["conversation_id"]

    detail = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert [m["content"] for m in detail.json()["messages"]] == [
        "/agent احسب (12 + 8) * 3",
        "حسبت العملية: الناتج 60.",
    ]


def test_agent_mode_streams_final_answer(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_agent.get_provider",
        lambda model=None: FakeToolProvider(),
    )
    token = _register_and_login(client, "agent-stream@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/chat/stream",
        json={"message": "/agent احسب 7 * 6"},
        headers=headers,
    )

    assert response.status_code == 200
    assert "event: conversation" in response.text
    assert "event: agent_tool" in response.text
    assert '"tool": "calculator"' in response.text
    assert '"status": "completed"' in response.text
    assert "event: chunk" in response.text
    assert "حسبت العملية: الناتج 60." in response.text
    assert "event: done" in response.text


def test_agent_command_requires_a_task(client):
    token = _register_and_login(client, "agent-empty@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/chat",
        json={"message": "/agent"},
        headers=headers,
    )

    assert response.status_code == 400


class FakePythonToolProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(api_key="test", base_url="http://example.test/v1", model="fake")

    async def get_reply_with_tools(self, messages, tools, tool_choice="auto"):
        if any(item.get("role") == "tool" for item in messages):
            return AIToolReply(text="الناتج من بايثون هو 42.")
        return AIToolReply(
            tool_calls=[
                AIToolCall(
                    id="call-python-1",
                    name="python",
                    arguments={"code": "print(6 * 7)"},
                )
            ]
        )


def test_agent_mode_uses_safe_python_tool(client, monkeypatch):
    monkeypatch.setattr(
        "app.services.ai_agent.get_provider",
        lambda model=None: FakePythonToolProvider(),
    )
    token = _register_and_login(client, "agent-python@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/chat",
        json={"message": "/agent استخدم بايثون لحساب 6*7"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "الناتج من بايثون هو 42."
