"""اختبارات الذاكرة المشتركة الخاصة بالمشاريع."""
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


def _create_project(client, headers, workspace_id, name):
    response = client.post(
        "/projects",
        json={"workspace_id": workspace_id, "name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_project_memory_crud(client):
    token = _register_and_login(client, "project-memory@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)
    project = _create_project(client, headers, workspace["id"], "Research")

    created = client.post(
        f"/projects/{project['id']}/memories",
        json={"content": "المستخدم يفضل أمثلة عملية قصيرة."},
        headers=headers,
    )
    assert created.status_code == 201
    memory = created.json()
    assert memory["project_id"] == project["id"]

    listed = client.get(
        f"/projects/{project['id']}/memories",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == memory["id"]

    updated = client.patch(
        f"/projects/{project['id']}/memories/{memory['id']}",
        json={"content": "المشروع يحتاج أمثلة عملية قصيرة."},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "المشروع يحتاج أمثلة عملية قصيرة."

    deleted = client.delete(
        f"/projects/{project['id']}/memories/{memory['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204


def test_project_memory_isolation_and_read_access(client):
    token = _register_and_login(client, "project-memory-isolation@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)
    project_a = _create_project(client, headers, workspace["id"], "A")
    project_b = _create_project(client, headers, workspace["id"], "B")

    created = client.post(
        f"/projects/{project_a['id']}/memories",
        json={"content": "معلومة خاصة بالمشروع A."},
        headers=headers,
    ).json()

    assert client.get(
        f"/projects/{project_b['id']}/memories",
        headers=headers,
    ).json() == []

    other_token = _register_and_login(client, "project-memory-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert client.get(
        f"/projects/{project_a['id']}/memories",
        headers=other_headers,
    ).status_code == 404
    assert client.patch(
        f"/projects/{project_a['id']}/memories/{created['id']}",
        json={"content": "اختراق"},
        headers=other_headers,
    ).status_code == 404


def test_project_memory_is_included_only_for_selected_project(client, monkeypatch):
    token = _register_and_login(client, "project-memory-chat@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)
    project_a = _create_project(client, headers, workspace["id"], "A")
    project_b = _create_project(client, headers, workspace["id"], "B")

    client.post(
        f"/projects/{project_a['id']}/memories",
        json={"content": "تفضيل سري للمشروع A."},
        headers=headers,
    )
    client.post(
        f"/projects/{project_b['id']}/memories",
        json={"content": "تفضيل سري للمشروع B."},
        headers=headers,
    )

    captured = []

    async def fake_get_ai_reply(message, history, model):
        captured.append(message)
        return AIReply(text="رد")

    monkeypatch.setattr(chat_router_module, "get_ai_reply", fake_get_ai_reply)

    response_a = client.post(
        "/chat",
        json={
            "message": "سؤال A",
            "workspace_id": workspace["id"],
            "project_id": project_a["id"],
        },
        headers=headers,
    )
    assert response_a.status_code == 200
    assert "تفضيل سري للمشروع A." in captured[-1]
    assert "تفضيل سري للمشروع B." not in captured[-1]

    response_none = client.post(
        "/chat",
        json={"message": "سؤال عام", "workspace_id": workspace["id"]},
        headers=headers,
    )
    assert response_none.status_code == 200
    assert "تفضيل سري للمشروع A." not in captured[-1]
    assert "تفضيل سري للمشروع B." not in captured[-1]
