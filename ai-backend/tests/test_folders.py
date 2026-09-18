"""اختبارات مجلدات المحادثات ونقل المحادثات بينها."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_folder_crud(client):
    token = _register_and_login(client, "folders@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/folders", json={"name": "Work"}, headers=headers)
    assert created.status_code == 201
    folder = created.json()
    assert folder["name"] == "Work"

    listed = client.get("/folders", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == folder["id"]

    renamed = client.patch(
        f"/folders/{folder['id']}",
        json={"name": "Work Projects"},
        headers=headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Work Projects"

    deleted = client.delete(f"/folders/{folder['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/folders", headers=headers).json() == []


def test_duplicate_folder_name_rejected_case_insensitively(client):
    token = _register_and_login(client, "folder-dup@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/folders", json={"name": "Work"}, headers=headers).status_code == 201
    duplicate = client.post("/folders", json={"name": " work "}, headers=headers)
    assert duplicate.status_code == 409


def test_cannot_manage_other_users_folder(client):
    token_a = _register_and_login(client, "folder-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    folder = client.post("/folders", json={"name": "Private"}, headers=headers_a).json()

    token_b = _register_and_login(client, "folder-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.patch(
        f"/folders/{folder['id']}",
        json={"name": "Hijacked"},
        headers=headers_b,
    ).status_code == 404
    assert client.delete(f"/folders/{folder['id']}", headers=headers_b).status_code == 404


def test_move_conversation_and_filter_by_folder(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "folder-chat@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    folder = client.post("/folders", json={"name": "Research"}, headers=headers).json()
    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة"},
        headers=headers,
    ).json()["conversation_id"]

    moved = client.patch(
        f"/conversations/{conversation_id}/folder",
        json={"folder_id": folder["id"]},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["folder_id"] == folder["id"]

    filtered = client.get(
        "/conversations",
        params={"folder_id": folder["id"]},
        headers=headers,
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [conversation_id]

    cleared = client.patch(
        f"/conversations/{conversation_id}/folder",
        json={"folder_id": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["folder_id"] is None


def test_cannot_move_conversation_to_other_users_folder(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "move-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    folder = client.post("/folders", json={"name": "Owner"}, headers=headers_a).json()
    conversation_id = client.post(
        "/chat",
        json={"message": "خاص"},
        headers=headers_a,
    ).json()["conversation_id"]

    token_b = _register_and_login(client, "move-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    response = client.patch(
        f"/conversations/{conversation_id}/folder",
        json={"folder_id": folder["id"]},
        headers=headers_b,
    )
    assert response.status_code == 404
