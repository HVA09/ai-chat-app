"""اختبار تكامل أمر بحث الويب داخل المحادثة."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.tools.web_search import WebSearchResult


def _register_and_login(client, email="web-search-chat@example.com"):
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_chat_web_search_command_does_not_call_ai(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(side_effect=AssertionError("AI provider must not be called")),
    )
    monkeypatch.setattr(
        chat_router_module,
        "search_web",
        AsyncMock(
            return_value=[
                WebSearchResult(
                    "Python",
                    "https://www.python.org/",
                    "Python is a programming language.",
                )
            ]
        ),
    )

    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/chat",
        json={"message": "/search python"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"].startswith("نتائج البحث")
    assert body["sources"][0]["id"] == "W1"
    assert body["sources"][0]["url"] == "https://www.python.org/"
