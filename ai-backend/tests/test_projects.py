"""اختبارات مشاريع مساحات العمل."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email: str, password: str = "StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _create_workspace(client, headers, name="Workspace"):
    response = client.post("/workspaces", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_project_crud_and_conversation_filter(client):
    monkeypatch = None
    token = _register_and_login(client, "project@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    created = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Study", "description": "Study project"},
        headers=headers,
    )
    assert created.status_code == 201
    project = created.json()

    listed = client.get(
        "/projects",
        params={"workspace_id": workspace["id"]},
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == project["id"]

    monkeypatch = AsyncMock(return_value=AIReply(text="رد"))
    import app.routers.chat as chat_router_module
    chat_router_module.get_ai_reply = monkeypatch
    conversation = client.post(
        "/chat",
        json={"message": "رسالة", "workspace_id": workspace["id"]},
        headers=headers,
    )
    assert conversation.status_code == 200
    conversation_id = conversation.json()["conversation_id"]

    moved = client.patch(
        f"/conversations/{conversation_id}/project",
        json={"project_id": project["id"]},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["project_id"] == project["id"]

    filtered = client.get(
        "/conversations",
        params={"workspace_id": workspace["id"], "project_id": project["id"]},
        headers=headers,
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [conversation_id]

    updated = client.patch(
        f"/projects/{project['id']}",
        json={"name": "Study 2", "description": "Updated"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Study 2"

    removed = client.delete(f"/projects/{project['id']}", headers=headers)
    assert removed.status_code == 204
    assert client.get(
        f"/projects",
        params={"workspace_id": workspace["id"]},
        headers=headers,
    ).json() == []
