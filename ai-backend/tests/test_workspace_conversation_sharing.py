"""اختبارات مشاركة المحادثات للقراءة فقط داخل مساحة العمل."""
from unittest.mock import AsyncMock

from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_owner_can_share_and_member_can_read_workspace_conversation(client, db_session, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )

    owner_token = _register_and_login(client, "workspace-share-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    workspace = client.post(
        "/workspaces",
        json={"name": "Team Research"},
        headers=owner_headers,
    ).json()

    conversation_id = client.post(
        "/chat",
        json={
            "message": "معلومة مشتركة",
            "workspace_id": workspace["id"],
        },
        headers=owner_headers,
    ).json()["conversation_id"]

    member_token = _register_and_login(client, "workspace-share-member@example.com")
    member = (
        db_session.query(User)
        .filter(User.email == "workspace-share-member@example.com")
        .one()
    )
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace["id"],
            user_id=member.id,
            role=WorkspaceRole.member,
        )
    )
    db_session.commit()

    share = client.post(
        f"/conversations/{conversation_id}/workspace-share",
        headers=owner_headers,
    )
    assert share.status_code == 201
    assert share.json()["workspace_id"] == workspace["id"]

    listed = client.get(
        f"/workspaces/{workspace['id']}/shared-conversations",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert listed.status_code == 200
    assert [item["conversation_id"] for item in listed.json()] == [conversation_id]

    detail = client.get(
        f"/workspaces/{workspace['id']}/shared-conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert detail.status_code == 200
    assert detail.json()["title"]
    assert len(detail.json()["messages"]) == 2


def test_non_member_cannot_read_shared_workspace_conversation(client, db_session, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )

    owner_token = _register_and_login(client, "workspace-share-owner-2@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    workspace = client.post(
        "/workspaces",
        json={"name": "Private Team"},
        headers=owner_headers,
    ).json()

    conversation_id = client.post(
        "/chat",
        json={
            "message": "سري",
            "workspace_id": workspace["id"],
        },
        headers=owner_headers,
    ).json()["conversation_id"]

    share = client.post(
        f"/conversations/{conversation_id}/workspace-share",
        headers=owner_headers,
    )
    assert share.status_code == 201

    member_token = _register_and_login(client, "workspace-share-outsider@example.com")
    response = client.get(
        f"/workspaces/{workspace['id']}/shared-conversations",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert response.status_code == 404


def test_owner_can_unshare_workspace_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )

    owner_token = _register_and_login(client, "workspace-share-owner-3@example.com")
    headers = {"Authorization": f"Bearer {owner_token}"}

    workspace = client.post(
        "/workspaces",
        json={"name": "Team"},
        headers=headers,
    ).json()

    conversation_id = client.post(
        "/chat",
        json={"message": "معلومة", "workspace_id": workspace["id"]},
        headers=headers,
    ).json()["conversation_id"]

    assert client.post(
        f"/conversations/{conversation_id}/workspace-share",
        headers=headers,
    ).status_code == 201
    assert client.get(
        f"/conversations/{conversation_id}/workspace-share",
        headers=headers,
    ).status_code == 200

    response = client.delete(
        f"/conversations/{conversation_id}/workspace-share",
        headers=headers,
    )
    assert response.status_code == 204
    assert client.get(
        f"/conversations/{conversation_id}/workspace-share",
        headers=headers,
    ).status_code == 404


def test_member_can_duplicate_shared_workspace_conversation(client, db_session, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )

    owner_token = _register_and_login(client, "workspace-duplicate-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Duplicate Team"},
        headers=owner_headers,
    ).json()

    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة مشتركة", "workspace_id": workspace["id"]},
        headers=owner_headers,
    ).json()["conversation_id"]

    member_token = _register_and_login(client, "workspace-duplicate-member@example.com")
    member = (
        db_session.query(User)
        .filter(User.email == "workspace-duplicate-member@example.com")
        .one()
    )
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace["id"],
            user_id=member.id,
            role=WorkspaceRole.member,
        )
    )
    db_session.commit()

    shared = client.post(
        f"/conversations/{conversation_id}/workspace-share",
        headers=owner_headers,
    )
    assert shared.status_code == 201

    duplicated = client.post(
        f"/workspaces/{workspace['id']}/shared-conversations/{conversation_id}/duplicate",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert duplicated.status_code == 201
    copied = duplicated.json()
    assert copied["id"] != conversation_id
    assert copied["title"].startswith("نسخة من")
    assert copied["workspace_id"] == workspace["id"]
    assert copied["folder_id"] is None
    assert copied["project_id"] is None
    assert copied["assistant_id"] is None
    assert copied["ai_model"] is None

    detail = client.get(
        f"/conversations/{copied['id']}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert detail.status_code == 200
    assert [message["content"] for message in detail.json()["messages"]] == [
        "رسالة مشتركة",
        "رد",
    ]


def test_non_member_cannot_duplicate_shared_workspace_conversation(client, db_session, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )

    owner_token = _register_and_login(client, "workspace-duplicate-owner-2@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Private Duplicate Team"},
        headers=owner_headers,
    ).json()

    conversation_id = client.post(
        "/chat",
        json={"message": "سر", "workspace_id": workspace["id"]},
        headers=owner_headers,
    ).json()["conversation_id"]

    assert client.post(
        f"/conversations/{conversation_id}/workspace-share",
        headers=owner_headers,
    ).status_code == 201

    outsider_token = _register_and_login(client, "workspace-duplicate-outsider@example.com")
    response = client.post(
        f"/workspaces/{workspace['id']}/shared-conversations/{conversation_id}/duplicate",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 404



def test_workspace_shared_detail_bounds_messages_and_source_metadata(
    client, db_session, monkeypatch
):
    from app.models.conversation import Message, MessageRole

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="reply")),
    )
    owner_token = _register_and_login(client, "workspace-bounds-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post("/workspaces", json={"name": "Bounds"}, headers=owner_headers).json()
    conversation_id = client.post(
        "/chat", json={"message": "initial", "workspace_id": workspace["id"]},
        headers=owner_headers,
    ).json()["conversation_id"]
    member_token = _register_and_login(client, "workspace-bounds-member@example.com")
    member = db_session.query(User).filter(User.email == "workspace-bounds-member@example.com").one()
    db_session.add(WorkspaceMember(workspace_id=workspace["id"], user_id=member.id, role=WorkspaceRole.member))
    db_session.commit()
    assert client.post(f"/conversations/{conversation_id}/workspace-share", headers=owner_headers).status_code == 201

    db_session.add_all([
        Message(
            conversation_id=conversation_id,
            role=MessageRole.user,
            content=f"bounded-{index}-" + ("x" * 25_000),
            sources=[{
                "id": f"S{index}", "filename": "source.txt",
                "file_id": 987654, "storage_key": "private/key",
                "url": "https://private.example/file", "snippet": "s" * 900,
                "provider_debug": "secret",
            }],
        )
        for index in range(105)
    ])
    db_session.commit()

    response = client.get(
        f"/workspaces/{workspace['id']}/shared-conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["messages"]) <= 100
    assert body["truncated"] is True
    assert sum(len(message["content"]) for message in body["messages"]) <= 100_000
    assert all(len(message["content"]) <= 20_000 for message in body["messages"])
    source = body["messages"][-1]["sources"][0]
    assert source["filename"] == "source.txt"
    assert len(source["snippet"]) <= 500
    assert "file_id" not in source
    assert "storage_key" not in source
    assert "url" not in source
    assert "provider_debug" not in source
