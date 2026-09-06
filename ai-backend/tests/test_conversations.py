"""
اختبارات مسارات المحادثات: القائمة والتفاصيل
"""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email="conv@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.json()["access_token"]


def test_list_conversations_empty(client):
    token = _register_and_login(client)
    response = client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_list_and_get_conversation_after_chat(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد تجريبي"))
    )
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    chat_response = client.post("/chat", json={"message": "أول رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]

    list_response = client.get("/conversations", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == conversation_id

    detail_response = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert len(body["messages"]) == 2  # رسالة المستخدم + رد المساعد


def test_get_other_users_conversation_returns_404(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد تجريبي"))
    )
    token_a = _register_and_login(client, "user_a@example.com")
    chat_response = client.post(
        "/chat",
        json={"message": "سر خاص بالمستخدم أ"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    conversation_id = chat_response.json()["conversation_id"]

    token_b = _register_and_login(client, "user_b@example.com")
    response = client.get(
        f"/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_conversations_require_authentication(client):
    response = client.get("/conversations")
    assert response.status_code == 401


def test_rename_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]

    response = client.patch(
        f"/conversations/{conversation_id}", json={"title": "اسم جديد"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["title"] == "اسم جديد"


def test_rename_rejects_blank_title(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]

    response = client.patch(
        f"/conversations/{conversation_id}", json={"title": "   "}, headers=headers
    )
    assert response.status_code == 422


def test_delete_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]

    delete_response = client.delete(f"/conversations/{conversation_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert get_response.status_code == 404


def test_cannot_rename_or_delete_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token_a = _register_and_login(client, "owner@example.com")
    chat_response = client.post(
        "/chat",
        json={"message": "خاص بالمالك"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    conversation_id = chat_response.json()["conversation_id"]

    token_b = _register_and_login(client, "intruder@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    rename_response = client.patch(
        f"/conversations/{conversation_id}", json={"title": "اختراق"}, headers=headers_b
    )
    assert rename_response.status_code == 404

    delete_response = client.delete(f"/conversations/{conversation_id}", headers=headers_b)
    assert delete_response.status_code == 404
