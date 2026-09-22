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


def _create_assistant(client, headers, name="Assistant", instructions="Help clearly."):
    response = client.post(
        "/assistants",
        json={
            "name": name,
            "instructions": instructions,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_project_crud_and_conversation_filter(client, monkeypatch):
    token = _register_and_login(client, "project@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    created = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "Study",
            "description": "Study project",
            "instructions": "Answer in Arabic and use practical examples.",
        },
        headers=headers,
    )
    assert created.status_code == 201
    project = created.json()
    assert project["instructions"] == "Answer in Arabic and use practical examples."

    listed = client.get(
        "/projects",
        params={"workspace_id": workspace["id"]},
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == project["id"]

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
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
        json={
            "name": "Study 2",
            "description": "Updated",
            "instructions": "Keep replies concise and structured.",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Study 2"
    assert updated.json()["instructions"] == "Keep replies concise and structured."

    removed = client.delete(f"/projects/{project['id']}", headers=headers)
    assert removed.status_code == 204
    assert client.get(
        f"/projects",
        params={"workspace_id": workspace["id"]},
        headers=headers,
    ).json() == []


def test_cannot_move_conversation_to_other_workspace_project(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    owner_token = _register_and_login(client, "project-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace_a = _create_workspace(client, owner_headers, "A")

    other_token = _register_and_login(client, "project-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    workspace_b = _create_workspace(client, other_headers, "B")

    project = client.post(
        "/projects",
        json={"workspace_id": workspace_b["id"], "name": "Private"},
        headers=other_headers,
    ).json()

    conversation = client.post(
        "/chat",
        json={"message": "رسالة", "workspace_id": workspace_a["id"]},
        headers=owner_headers,
    )
    conversation_id = conversation.json()["conversation_id"]

    response = client.patch(
        f"/conversations/{conversation_id}/project",
        json={"project_id": project["id"]},
        headers=owner_headers,
    )
    assert response.status_code == 404


def test_project_instructions_are_applied_to_chat(client, monkeypatch):
    token = _register_and_login(client, "project-instructions@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    project = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "Python",
            "instructions": "Explain in Arabic, step by step, with one exercise.",
        },
        headers=headers,
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    captured = {}

    async def fake_get_ai_reply(message, history, model):
        captured["message"] = message
        captured["history"] = history
        captured["model"] = model
        return AIReply(text="رد")

    monkeypatch.setattr(chat_router_module, "get_ai_reply", fake_get_ai_reply)

    response = client.post(
        "/chat",
        json={
            "message": "اشرح المتغيرات",
            "workspace_id": workspace["id"],
            "project_id": project_id,
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert "[PROJECT INSTRUCTIONS]" in captured["message"]
    assert "Explain in Arabic, step by step, with one exercise." in captured["message"]


def test_project_instructions_are_scoped_to_project(client, monkeypatch):
    token = _register_and_login(client, "project-instructions-scope@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    first = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "A",
            "instructions": "Private project guidance A",
        },
        headers=headers,
    ).json()
    second = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "B",
            "instructions": "Private project guidance B",
        },
        headers=headers,
    ).json()

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
            "project_id": first["id"],
        },
        headers=headers,
    )
    assert response_a.status_code == 200
    assert "Private project guidance A" in captured[-1]
    assert "Private project guidance B" not in captured[-1]

    response_none = client.post(
        "/chat",
        json={
            "message": "سؤال عام",
            "workspace_id": workspace["id"],
        },
        headers=headers,
    )
    assert response_none.status_code == 200
    assert "Private project guidance A" not in captured[-1]
    assert "Private project guidance B" not in captured[-1]

    response_b = client.post(
        "/chat",
        json={
            "message": "سؤال B",
            "workspace_id": workspace["id"],
            "project_id": second["id"],
        },
        headers=headers,
    )
    assert response_b.status_code == 200
    assert "Private project guidance B" in captured[-1]
    assert "Private project guidance A" not in captured[-1]

def test_project_default_assistant_is_used_and_explicit_override_wins(client, monkeypatch):
    token = _register_and_login(client, "project-assistant@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    default_assistant = _create_assistant(
        client,
        headers,
        name="Project Helper",
        instructions="Always explain project work step by step.",
    )
    explicit_assistant = _create_assistant(
        client,
        headers,
        name="Explicit Helper",
        instructions="Use concise answers.",
    )

    created = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "Python",
            "assistant_id": default_assistant["id"],
        },
        headers=headers,
    )
    assert created.status_code == 201
    project = created.json()
    assert project["assistant_id"] == default_assistant["id"]

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )

    implicit = client.post(
        "/chat",
        json={
            "message": "سؤال المشروع",
            "workspace_id": workspace["id"],
            "project_id": project["id"],
        },
        headers=headers,
    )
    assert implicit.status_code == 200
    implicit_id = implicit.json()["conversation_id"]
    implicit_detail = client.get(
        f"/conversations/{implicit_id}",
        headers=headers,
    )
    assert implicit_detail.status_code == 200
    assert implicit_detail.json()["assistant_id"] == default_assistant["id"]

    explicit = client.post(
        "/chat",
        json={
            "message": "سؤال صريح",
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "assistant_id": explicit_assistant["id"],
        },
        headers=headers,
    )
    assert explicit.status_code == 200
    explicit_id = explicit.json()["conversation_id"]
    explicit_detail = client.get(
        f"/conversations/{explicit_id}",
        headers=headers,
    )
    assert explicit_detail.status_code == 200
    assert explicit_detail.json()["assistant_id"] == explicit_assistant["id"]


def test_project_rejects_inaccessible_default_assistant(client):
    owner_token = _register_and_login(client, "project-assistant-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _create_workspace(client, owner_headers)

    other_token = _register_and_login(client, "project-assistant-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    other_assistant = _create_assistant(client, other_headers, name="Private")

    response = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "Private Project",
            "assistant_id": other_assistant["id"],
        },
        headers=owner_headers,
    )
    assert response.status_code == 404


