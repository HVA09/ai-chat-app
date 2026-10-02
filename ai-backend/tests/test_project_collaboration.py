"""F4 project collaboration access tests."""
from unittest.mock import AsyncMock

from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email: str):
    client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _workspace(client, token, name="Workspace"):
    response = client.post(
        "/workspaces",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def _add_workspace_member(db_session, workspace_id: int, user_email: str):
    user = db_session.query(User).filter(User.email == user_email).one()
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=WorkspaceRole.member,
        )
    )
    db_session.commit()
    return user


def test_project_owner_can_add_member_and_workspace_member_can_read(client, db_session):
    owner_token = _register_and_login(client, "project-collab-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _workspace(client, owner_token, "Collaboration")

    member_token = _register_and_login(client, "project-collab-member@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}
    _add_workspace_member(db_session, workspace["id"], "project-collab-member@example.com")

    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Shared"},
        headers=owner_headers,
    ).json()

    added = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": db_session.query(User).filter(User.email == "project-collab-member@example.com").one().id, "role": "viewer"},
        headers=owner_headers,
    )
    assert added.status_code == 201
    assert added.json()["role"] == "viewer"

    listed = client.get(f"/projects/{project['id']}/members", headers=member_headers)
    assert listed.status_code == 200
    assert any(item["email"] == "project-collab-member@example.com" for item in listed.json())

    projects = client.get(
        "/projects",
        params={"workspace_id": workspace["id"]},
        headers=member_headers,
    )
    assert projects.status_code == 200
    assert [item["id"] for item in projects.json()] == [project["id"]]


def test_viewer_can_read_project_files_but_cannot_edit(client, db_session):
    owner_token = _register_and_login(client, "project-viewer-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _workspace(client, owner_token, "Viewer")

    member_token = _register_and_login(client, "project-viewer@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}
    member = _add_workspace_member(db_session, workspace["id"], "project-viewer@example.com")

    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Viewer Project"},
        headers=owner_headers,
    ).json()
    client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": member.id, "role": "viewer"},
        headers=owner_headers,
    )
    created = client.post(
        f"/projects/{project['id']}/files",
        json={"path": "README.md", "content": "hello"},
        headers=owner_headers,
    )
    assert created.status_code == 201

    file_id = created.json()["id"]
    readable = client.get(
        f"/projects/{project['id']}/files/{file_id}",
        headers=member_headers,
    )
    assert readable.status_code == 200

    denied = client.patch(
        f"/projects/{project['id']}/files/{file_id}",
        json={"path": "README.md", "content": "changed"},
        headers=member_headers,
    )
    assert denied.status_code == 403


def test_editor_can_edit_and_manager_can_manage_members(client, db_session):
    owner_token = _register_and_login(client, "project-editor-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _workspace(client, owner_token, "Editor")

    editor_token = _register_and_login(client, "project-editor@example.com")
    editor_headers = {"Authorization": f"Bearer {editor_token}"}
    editor = _add_workspace_member(db_session, workspace["id"], "project-editor@example.com")

    third_token = _register_and_login(client, "project-third@example.com")
    _ = third_token
    third = _add_workspace_member(db_session, workspace["id"], "project-third@example.com")

    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Editor Project"},
        headers=owner_headers,
    ).json()
    added = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": editor.id, "role": "editor"},
        headers=owner_headers,
    )
    assert added.status_code == 201

    created = client.post(
        f"/projects/{project['id']}/files",
        json={"path": "app.js", "content": "one"},
        headers=owner_headers,
    )
    file_id = created.json()["id"]

    updated = client.patch(
        f"/projects/{project['id']}/files/{file_id}",
        json={"path": "app.js", "content": "two"},
        headers=editor_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "two"

    member_id = added.json()["id"]
    promoted = client.patch(
        f"/projects/{project['id']}/members/{member_id}",
        json={"role": "manager"},
        headers=owner_headers,
    )
    assert promoted.status_code == 200

    manager_add = client.post(
        f"/projects/{project['id']}/members",
        json={"user_id": third.id, "role": "viewer"},
        headers=editor_headers,
    )
    assert manager_add.status_code == 201


def test_project_member_access_isolated_from_workspace_and_chat(client, db_session, monkeypatch):
    owner_token = _register_and_login(client, "project-isolation-owner-f4@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _workspace(client, owner_token, "Isolation")

    member_token = _register_and_login(client, "project-isolation-member-f4@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}
    _add_workspace_member(db_session, workspace["id"], "project-isolation-member-f4@example.com")

    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Private"},
        headers=owner_headers,
    ).json()

    projects = client.get(
        "/projects",
        params={"workspace_id": workspace["id"]},
        headers=member_headers,
    )
    assert projects.status_code == 200
    assert projects.json() == []

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="reply")),
    )
    chat = client.post(
        "/chat",
        json={
            "message": "private",
            "workspace_id": workspace["id"],
            "project_id": project["id"],
        },
        headers=member_headers,
    )
    assert chat.status_code == 404

    direct = client.get(
        f"/projects/{project['id']}/members",
        headers=member_headers,
    )
    assert direct.status_code == 404
