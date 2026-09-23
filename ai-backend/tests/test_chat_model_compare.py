"""اختبارات مقارنة نموذجين للذكاء الاصطناعي."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return client.cookies.get("access_token")


def test_compare_two_allowed_models(client, monkeypatch):
    token = _register_and_login(client, "compare@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    monkeypatch.setattr(
        chat_router_module,
        "get_allowed_ai_models",
        lambda *_args, **_kwargs: ["model-a", "model-b"],
    )

    async def fake_reply(message, history, model):
        return AIReply(
            text=f"reply from {model}",
            input_tokens=10,
            output_tokens=20,
            provider="test-provider",
            latency_ms=15,
        )

    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(side_effect=fake_reply))

    response = client.post(
        "/chat/compare",
        json={
            "message": "قارن الإجابتين",
            "model_a": "model-a",
            "model_b": "model-b",
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["model"] for item in body["results"]] == ["model-a", "model-b"]
    assert body["results"][0]["text"] == "reply from model-a"
    assert body["results"][1]["text"] == "reply from model-b"


def test_compare_rejects_same_model(client, monkeypatch):
    token = _register_and_login(client, "compare-same@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(
        chat_router_module,
        "get_allowed_ai_models",
        lambda *_args, **_kwargs: ["model-a", "model-b"],
    )

    response = client.post(
        "/chat/compare",
        json={
            "message": "سؤال",
            "model_a": "model-a",
            "model_b": "model-a",
        },
        headers=headers,
    )

    assert response.status_code == 400
