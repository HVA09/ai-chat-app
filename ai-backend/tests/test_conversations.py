"""
اختبارات مسارات المحادثات: القائمة والتفاصيل
"""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email="conv@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_list_conversations_empty(client):
    token = _register_and_login(client)
    response = client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_list_and_get_conversation_after_chat(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد تجريبي")))
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
    assert len(detail_response.json()["messages"]) == 2


def test_get_other_users_conversation_returns_404(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد تجريبي")))
    token_a = _register_and_login(client, "user_a@example.com")
    chat_response = client.post("/chat", json={"message": "سر خاص بالمستخدم أ"}, headers={"Authorization": f"Bearer {token_a}"})
    conversation_id = chat_response.json()["conversation_id"]
    token_b = _register_and_login(client, "user_b@example.com")
    response = client.get(f"/conversations/{conversation_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404


def test_conversations_require_authentication(client):
    response = client.get("/conversations")
    assert response.status_code == 401


def test_toggle_pin_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "pin@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]

    first = client.get("/conversations", headers=headers)
    assert first.json()[0]["is_pinned"] is False

    response = client.patch(f"/conversations/{conversation_id}/pin", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_pinned"] is True

    second = client.get("/conversations", headers=headers)
    assert second.json()[0]["is_pinned"] is True

    response = client.patch(f"/conversations/{conversation_id}/pin", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_pinned"] is False


def test_cannot_pin_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "pin-owner@example.com")
    chat_response = client.post(
        "/chat",
        json={"message": "خاص"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    conversation_id = chat_response.json()["conversation_id"]

    token_b = _register_and_login(client, "pin-other@example.com")
    response = client.patch(
        f"/conversations/{conversation_id}/pin",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_toggle_archive_conversation_and_filter(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "archive@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]

    response = client.patch(f"/conversations/{conversation_id}/archive", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_archived"] is True

    normal = client.get("/conversations", headers=headers)
    assert normal.json() == []

    archived = client.get(
        "/conversations",
        params={"include_archived": True},
        headers=headers,
    )
    assert len(archived.json()) == 1
    assert archived.json()[0]["is_archived"] is True

    response = client.patch(f"/conversations/{conversation_id}/archive", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_archived"] is False


def test_rename_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]
    response = client.patch(f"/conversations/{conversation_id}", json={"title": "اسم جديد"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "اسم جديد"


def test_rename_rejects_blank_title(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]
    response = client.patch(f"/conversations/{conversation_id}", json={"title": "   "}, headers=headers)
    assert response.status_code == 422


def test_export_conversation_markdown(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تجريبي")),
    )
    token = _register_and_login(client, "export@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post(
        "/chat",
        json={"message": "أول رسالة للتصدير"},
        headers=headers,
    )
    conversation_id = chat_response.json()["conversation_id"]

    response = client.get(
        f"/conversations/{conversation_id}/export",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert "# محادثة جديدة" in response.text
    assert "أول رسالة للتصدير" in response.text
    assert "رد تجريبي" in response.text


def test_cannot_export_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "export-owner@example.com")
    chat_response = client.post(
        "/chat",
        json={"message": "خاص"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    conversation_id = chat_response.json()["conversation_id"]

    token_b = _register_and_login(client, "export-other@example.com")
    response = client.get(
        f"/conversations/{conversation_id}/export",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_delete_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]
    delete_response = client.delete(f"/conversations/{conversation_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/conversations/{conversation_id}", headers=headers).status_code == 404


def test_cannot_rename_or_delete_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token_a = _register_and_login(client, "owner@example.com")
    chat_response = client.post("/chat", json={"message": "خاص بالمالك"}, headers={"Authorization": f"Bearer {token_a}"})
    conversation_id = chat_response.json()["conversation_id"]
    token_b = _register_and_login(client, "intruder@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    rename_response = client.patch(f"/conversations/{conversation_id}", json={"title": "اختراق"}, headers=headers_b)
    assert rename_response.status_code == 404
    delete_response = client.delete(f"/conversations/{conversation_id}", headers=headers_b)
    assert delete_response.status_code == 404
