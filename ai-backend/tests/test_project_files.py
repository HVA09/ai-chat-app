"""اختبارات ملفات مصدر المشاريع."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.models.conversation import Conversation
from app.models.user import User
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply
from app.services.tools.registry import ToolContext, tool_registry



def _register_and_login(client, email: str, password: str = "StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _create_workspace(client, headers, name="Workspace"):
    response = client.post("/workspaces", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_project_file_crud_and_path_safety(client):
    token = _register_and_login(client, "project-files@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    project_response = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "App"},
        headers=headers,
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    created = client.post(
        f"/projects/{project_id}/files",
        json={
            "path": "src/App.jsx",
            "content": "export default function App() { return null; }",
        },
        headers=headers,
    )
    assert created.status_code == 201
    project_file = created.json()
    assert project_file["path"] == "src/App.jsx"
    assert project_file["content"].startswith("export default")

    listed = client.get(
        f"/projects/{project_id}/files",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["path"] == "src/App.jsx"
    assert listed.json()[0]["content_length"] == len(project_file["content"])
    assert "content" not in listed.json()[0]

    detail = client.get(
        f"/projects/{project_id}/files/{project_file['id']}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["content"] == project_file["content"]

    updated = client.patch(
        f"/projects/{project_id}/files/{project_file['id']}",
        json={
            "path": "src/main.jsx",
            "content": "export default function App() { return <main />; }",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["path"] == "src/main.jsx"

    duplicate = client.post(
        f"/projects/{project_id}/files",
        json={"path": "src/main.jsx", "content": "duplicate"},
        headers=headers,
    )
    assert duplicate.status_code == 409

    from pydantic import ValidationError
    from app.schemas.project_files import ProjectFileCreate

    with pytest.raises(ValidationError):
        ProjectFileCreate(path="../secret.txt", content="nope")

    removed = client.delete(
        f"/projects/{project_id}/files/{project_file['id']}",
        headers=headers,
    )
    assert removed.status_code == 204

    assert client.get(
        f"/projects/{project_id}/files",
        headers=headers,
    ).json() == []


def test_project_files_are_isolated_across_workspaces(client):
    owner_token = _register_and_login(client, "project-file-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner_workspace = _create_workspace(client, owner_headers, "Owner")

    other_token = _register_and_login(client, "project-file-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    other_workspace = _create_workspace(client, other_headers, "Other")
    project = client.post(
        "/projects",
        json={"workspace_id": other_workspace["id"], "name": "Private"},
        headers=other_headers,
    ).json()

    response = client.get(
        f"/projects/{project['id']}/files",
        headers=owner_headers,
    )
    assert response.status_code == 404

    response = client.post(
        f"/projects/{project['id']}/files",
        json={"path": "secret.txt", "content": "private"},
        headers=owner_headers,
    )
    assert response.status_code == 404

    assert owner_workspace["id"] != other_workspace["id"]


def test_agent_can_edit_project_file_with_bounded_diff(client, db_session, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "project-agent-edit@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers, "Agent Workspace")

    project_response = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Agent App"},
        headers=headers,
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    conversation_response = client.post(
        "/chat",
        json={"message": "init", "workspace_id": workspace["id"]},
        headers=headers,
    )
    assert conversation_response.status_code == 200
    conversation_id = conversation_response.json()["conversation_id"]

    moved = client.patch(
        f"/conversations/{conversation_id}/project",
        json={"project_id": project_id},
        headers=headers,
    )
    assert moved.status_code == 200

    created = client.post(
        f"/projects/{project_id}/files",
        json={"path": "src/App.jsx", "content": "export default function App() { return null; }"},
        headers=headers,
    )
    assert created.status_code == 201

    current_user = db_session.query(User).filter(User.email == "project-agent-edit@example.com").one()
    conversation = db_session.get(Conversation, conversation_id)
    result = asyncio.run(
        tool_registry.execute(
            "edit_project_file",
            {
                "path": "src/App.jsx",
                "content": "export default function App() { return <main />; }",
                "expected_content": "export default function App() { return null; }",
            },
            ToolContext(
                conversation=conversation,
                current_user=current_user,
                db=db_session,
            ),
        )
    )
    assert result.succeeded is True
    assert "src/App.jsx" in result.content
    assert "Diff:" in result.content
    assert "-export default function App() { return null; }" in result.content
    assert "+export default function App() { return <main />; }" in result.content

    detail = client.get(
        f"/projects/{project_id}/files/{created.json()['id']}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["content"].endswith("return <main />; }")

    stale = asyncio.run(
        tool_registry.execute(
            "edit_project_file",
            {
                "path": "src/App.jsx",
                "content": "stale",
                "expected_content": "old-content",
            },
            ToolContext(
                conversation=conversation,
                current_user=current_user,
                db=db_session,
            ),
        )
    )
    assert stale.succeeded is False
    assert "تغيّر منذ آخر قراءة" in stale.content

    unsafe = asyncio.run(
        tool_registry.execute(
            "edit_project_file",
            {
                "path": "../secret.txt",
                "content": "blocked",
            },
            ToolContext(
                conversation=conversation,
                current_user=current_user,
                db=db_session,
            ),
        )
    )
    assert unsafe.succeeded is False
    assert "غير آمن" in unsafe.content
