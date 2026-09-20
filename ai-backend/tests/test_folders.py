"""اختبارات مجلدات المحادثات ونقل المحادثات بينها."""
from unittest.mock import AsyncMock

from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
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


def _create_workspace(client, headers, name):
    response = client.post("/workspaces", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_workspace_folders_are_visible_only_inside_the_workspace(client):
    token = _register_and_login(client, "folder-workspace-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace_a = _create_workspace(client, headers, "Team A")
    workspace_b = _create_workspace(client, headers, "Team B")

    created = client.post(
        "/folders",
        json={"name": "Research", "workspace_id": workspace_a["id"]},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["workspace_id"] == workspace_a["id"]

    in_a = client.get(
        "/folders",
        params={"workspace_id": workspace_a["id"]},
        headers=headers,
    )
    assert [item["name"] for item in in_a.json()] == ["Research"]

    in_b = client.get(
        "/folders",
        params={"workspace_id": workspace_b["id"]},
        headers=headers,
    )
    assert in_b.status_code == 200
    assert all(item["name"] != "Research" for item in in_b.json())


def test_workspace_members_can_use_but_not_manage_workspace_folder(client, db_session):
    token_owner = _register_and_login(client, "folder-ws-owner@example.com")
    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    workspace = _create_workspace(client, headers_owner, "Shared Team")

    token_member = _register_and_login(client, "folder-ws-member@example.com")
    user_row = db_session.query(User).filter_by(
        email="folder-ws-member@example.com"
    ).first()

    db_session.add(
        WorkspaceMember(
            workspace_id=workspace["id"],
            user_id=user_row.id,
            role=WorkspaceRole.member,
        )
    )
    db_session.commit()

    headers_member = {"Authorization": f"Bearer {token_member}"}
    folder = client.post(
        "/folders",
        json={"name": "Shared", "workspace_id": workspace["id"]},
        headers=headers_owner,
    ).json()

    listed = client.get(
        "/folders",
        params={"workspace_id": workspace["id"]},
        headers=headers_member,
    )
    assert listed.status_code == 200
    assert any(item["id"] == folder["id"] for item in listed.json())

    rename = client.patch(
        f"/folders/{folder['id']}",
        json={"name": "Blocked"},
        headers=headers_member,
    )
    assert rename.status_code == 403

    delete = client.delete(
        f"/folders/{folder['id']}",
        headers=headers_member,
    )
    assert delete.status_code == 403


def test_workspace_folder_names_can_repeat_across_workspaces(client):
    token = _register_and_login(client, "folder-same-name@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace_a = _create_workspace(client, headers, "Alpha")
    workspace_b = _create_workspace(client, headers, "Beta")

    first = client.post(
        "/folders",
        json={"name": "Projects", "workspace_id": workspace_a["id"]},
        headers=headers,
    )
    second = client.post(
        "/folders",
        json={"name": "Projects", "workspace_id": workspace_b["id"]},
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201


def test_workspace_folder_cannot_receive_conversation_from_other_workspace(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "folder-cross-workspace@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace_a = _create_workspace(client, headers, "Client A")
    workspace_b = _create_workspace(client, headers, "Client B")

    folder_b = client.post(
        "/folders",
        json={"name": "Only B", "workspace_id": workspace_b["id"]},
        headers=headers,
    ).json()

    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة", "workspace_id": workspace_a["id"]},
        headers=headers,
    ).json()["conversation_id"]

    moved = client.patch(
        f"/conversations/{conversation_id}/folder",
        json={"folder_id": folder_b["id"]},
        headers=headers,
    )
    assert moved.status_code == 409
