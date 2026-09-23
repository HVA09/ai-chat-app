"""اختبارات تعليقات المحادثات المشتركة."""
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


def _setup_shared_conversation(client, db_session, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تجريبي")),
    )

    owner_token = _register_and_login(client, "comments-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Comments Team"},
        headers=owner_headers,
    ).json()
    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة مشتركة", "workspace_id": workspace["id"]},
        headers=owner_headers,
    ).json()["conversation_id"]

    member_token = _register_and_login(client, "comments-member@example.com")
    member = (
        db_session.query(User)
        .filter(User.email == "comments-member@example.com")
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

    assert client.post(
        f"/conversations/{conversation_id}/workspace-share",
        headers=owner_headers,
    ).status_code == 201

    return workspace["id"], conversation_id, owner_headers, {
        "Authorization": f"Bearer {member_token}"
    }


def test_member_can_list_and_create_comment(client, db_session, monkeypatch):
    workspace_id, conversation_id, owner_headers, member_headers = _setup_shared_conversation(
        client, db_session, monkeypatch
    )

    listed = client.get(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments",
        headers=member_headers,
    )
    assert listed.status_code == 200
    assert listed.json() == []

    created = client.post(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments",
        json={"content": "ملاحظة مهمة"},
        headers=member_headers,
    )
    assert created.status_code == 201
    assert created.json()["content"] == "ملاحظة مهمة"
    assert created.json()["user_email"] == "comments-member@example.com"

    listed = client.get(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments",
        headers=owner_headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    owner_notifications = client.get(
        "/notifications",
        headers=owner_headers,
    )
    assert owner_notifications.status_code == 200
    comment_notifications = [
        item for item in owner_notifications.json()
        if item["notification_type"] == "workspace_comment"
    ]
    assert len(comment_notifications) == 1
    assert "comments-member@example.com" in comment_notifications[0]["body"]

    member_notifications = client.get(
        "/notifications",
        headers=member_headers,
    )
    assert member_notifications.status_code == 200
    assert all(
        item["notification_type"] != "workspace_comment"
        for item in member_notifications.json()
    )


def test_comment_can_target_message_and_validate_scope(client, db_session, monkeypatch):
    workspace_id, conversation_id, owner_headers, member_headers = _setup_shared_conversation(
        client, db_session, monkeypatch
    )

    detail = client.get(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}",
        headers=member_headers,
    ).json()
    message_id = None
    # The shared-detail endpoint intentionally exposes content, not ids. Use the owner detail.
    owner_detail = client.get(
        f"/conversations/{conversation_id}",
        headers=owner_headers,
    ).json()
    message_id = owner_detail["messages"][0]["id"]

    created = client.post(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments",
        json={"content": "راجع هذه الرسالة", "message_id": message_id},
        headers=member_headers,
    )
    assert created.status_code == 201
    assert created.json()["message_id"] == message_id

    bad = client.post(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments",
        json={"content": "تعليق", "message_id": 999999999},
        headers=member_headers,
    )
    assert bad.status_code == 404


def test_comment_author_can_update_and_delete(client, db_session, monkeypatch):
    workspace_id, conversation_id, owner_headers, member_headers = _setup_shared_conversation(
        client, db_session, monkeypatch
    )

    created = client.post(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments",
        json={"content": "قديم"},
        headers=member_headers,
    ).json()

    updated = client.patch(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments/{created['id']}",
        json={"content": "محدّث"},
        headers=member_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "محدّث"

    deleted = client.delete(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments/{created['id']}",
        headers=member_headers,
    )
    assert deleted.status_code == 204


def test_other_member_cannot_edit_comment_but_workspace_admin_can_delete(client, db_session, monkeypatch):
    workspace_id, conversation_id, owner_headers, member_headers = _setup_shared_conversation(
        client, db_session, monkeypatch
    )

    created = client.post(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments",
        json={"content": "تعليق"},
        headers=member_headers,
    ).json()

    other_token = _register_and_login(client, "comments-other@example.com")
    other = (
        db_session.query(User)
        .filter(User.email == "comments-other@example.com")
        .one()
    )
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace_id,
            user_id=other.id,
            role=WorkspaceRole.member,
        )
    )
    db_session.commit()
    other_headers = {"Authorization": f"Bearer {other_token}"}

    forbidden = client.patch(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments/{created['id']}",
        json={"content": "لا"},
        headers=other_headers,
    )
    assert forbidden.status_code == 403

    admin_token = _register_and_login(client, "comments-admin@example.com")
    admin = (
        db_session.query(User)
        .filter(User.email == "comments-admin@example.com")
        .one()
    )
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace_id,
            user_id=admin.id,
            role=WorkspaceRole.admin,
        )
    )
    db_session.commit()

    deleted = client.delete(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments/{created['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deleted.status_code == 204


def test_non_member_cannot_use_comments(client, db_session, monkeypatch):
    workspace_id, conversation_id, owner_headers, _ = _setup_shared_conversation(
        client, db_session, monkeypatch
    )
    outsider_token = _register_and_login(client, "comments-outsider@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    assert client.get(
        f"/workspaces/{workspace_id}/shared-conversations/{conversation_id}/comments",
        headers=outsider_headers,
    ).status_code == 404
