"""اختبارات مساحات العمل الأساسية وربط المحادثات بها."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_registration_creates_personal_workspace(client):
    token = _register_and_login(client, "workspace-personal@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/workspaces", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Personal"
    assert response.json()[0]["role"] == "owner"


def test_create_and_rename_workspace(client):
    token = _register_and_login(client, "workspace-crud@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/workspaces",
        json={"name": "Research Team"},
        headers=headers,
    )
    assert created.status_code == 201
    workspace = created.json()
    assert workspace["role"] == "owner"

    renamed = client.patch(
        f"/workspaces/{workspace['id']}",
        json={"name": "Research"},
        headers=headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Research"


def test_duplicate_workspace_name_rejected(client):
    token = _register_and_login(client, "workspace-dup@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/workspaces", json={"name": "Research"}, headers=headers).status_code == 201
    duplicate = client.post(
        "/workspaces",
        json={"name": " research "},
        headers=headers,
    )
    assert duplicate.status_code == 409


def test_chat_belongs_to_selected_workspace(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "workspace-chat@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/workspaces",
        json={"name": "Client A"},
        headers=headers,
    ).json()

    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة", "workspace_id": created["id"]},
        headers=headers,
    ).json()["conversation_id"]

    listed = client.get(
        "/conversations",
        params={"workspace_id": created["id"]},
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == conversation_id
    assert listed.json()[0]["workspace_id"] == created["id"]


def test_cannot_chat_in_other_users_workspace(client):
    monkeypatch = AsyncMock(return_value=AIReply(text="رد"))
    chat_router_module.get_ai_reply = monkeypatch
    token_a = _register_and_login(client, "workspace-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Private"},
        headers=headers_a,
    ).json()

    token_b = _register_and_login(client, "workspace-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    response = client.post(
        "/chat",
        json={"message": "اختبار", "workspace_id": workspace["id"]},
        headers=headers_b,
    )
    assert response.status_code == 404
