"""اختبارات أداة الآلة الحاسبة."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.tools.calculator import CalculatorError, calculate_expression, extract_calculator_expression


def _register_and_login(client, email="tool@example.com"):
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    response = client.post("/auth/login", json={"email": email, "password": "StrongPass123"})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_calculator_expression():
    assert calculate_expression("(12 + 8) * 3") == "60"
    assert calculate_expression("2 ** 5") == "32"


def test_calculator_rejects_unsafe_expression():
    try:
        calculate_expression("__import__('os').system('echo hacked')")
    except CalculatorError:
        pass
    else:
        raise AssertionError("unsafe expression was accepted")


def test_calculator_rejects_division_by_zero():
    try:
        calculate_expression("10 / 0")
    except CalculatorError as exc:
        assert "القسمة على صفر" in str(exc)
    else:
        raise AssertionError("division by zero was accepted")


def test_extract_calculator_command():
    assert extract_calculator_expression("/calc 2 + 3") == "2 + 3"
    assert extract_calculator_expression("/calculate 7 * 6") == "7 * 6"
    assert extract_calculator_expression("ما هو 2 + 3؟") is None


def test_chat_calculator_command_does_not_call_ai(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(side_effect=AssertionError("AI provider must not be called")),
    )
    token = _register_and_login(client, "tool-chat@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/chat",
        json={"message": "/calc (12 + 8) * 3"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "60"
    conversation_id = response.json()["conversation_id"]

    detail = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert detail.status_code == 200
    assert [m["content"] for m in detail.json()["messages"]] == [
        "/calc (12 + 8) * 3",
        "60",
    ]


def test_invalid_chat_calculator_command_returns_400(client):
    token = _register_and_login(client, "tool-invalid@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/chat",
        json={"message": "/calc 2 / 0"},
        headers=headers,
    )
    assert response.status_code == 400

def test_chat_stream_calculator_command_does_not_call_ai(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "stream_ai_reply",
        AsyncMock(side_effect=AssertionError("AI provider must not be called")),
    )
    token = _register_and_login(client, "tool-stream@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/chat/stream",
        json={"message": "/calc 7 * 6"},
        headers=headers,
    )

    assert response.status_code == 200
    assert "event: conversation" in response.text
    assert "event: chunk\ndata: 42" in response.text
    assert "event: done" in response.text

