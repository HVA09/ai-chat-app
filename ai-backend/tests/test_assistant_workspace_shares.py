"""اختبارات مشاركة المساعدين داخل مساحة العمل."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _create_workspace(client, token, name="Team"):
    response = client.post(
        "/workspaces",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_share_list_unshare_assistant(client):
    owner_token = _register_and_login(client, "assistant-share-owner@example.com")
    member_token = _register_and_login(client, "assistant-share-member@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    member_headers = {"Authorization": f"Bearer {member_token}"}

    workspace_id = _create_workspace(client, owner_token)
    invite = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "assistant-share-member@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invite.status_code in {200, 201}

    assistant = client.post(
        "/assistants",
        json={
            "name": "Team Tutor",
            "description": "مساعد الفريق",
            "instructions": "أجب بخطوات مختصرة.",
        },
        headers=owner_headers,
    ).json()

    shared = client.post(
        f"/assistants/{assistant['id']}/workspace-share/{workspace_id}",
        headers=owner_headers,
    )
    assert shared.status_code == 201

    listed = client.get(
        f"/workspaces/{workspace_id}/shared-assistants",
        headers=member_headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == assistant["id"]
    assert listed.json()[0]["can_edit"] is False

    unshared = client.delete(
        f"/assistants/{assistant['id']}/workspace-share/{workspace_id}",
        headers=owner_headers,
    )
    assert unshared.status_code == 204
    assert client.get(
        f"/workspaces/{workspace_id}/shared-assistants",
        headers=member_headers,
    ).json() == []


def test_shared_assistant_can_be_used_in_chat(client, monkeypatch):
    mock_reply = AsyncMock(return_value=AIReply(text="رد مشترك"))
    monkeypatch.setattr(chat_router_module, "get_ai_reply", mock_reply)

    owner_token = _register_and_login(client, "shared-chat-owner@example.com")
    member_token = _register_and_login(client, "shared-chat-member@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    member_headers = {"Authorization": f"Bearer {member_token}"}
    workspace_id = _create_workspace(client, owner_token)

    invite = client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "shared-chat-member@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invite.status_code in {200, 201}

    assistant = client.post(
        "/assistants",
        json={"name": "Shared Coach", "instructions": "استخدم أسلوبًا عمليًا."},
        headers=owner_headers,
    ).json()
    assert client.post(
        f"/assistants/{assistant['id']}/workspace-share/{workspace_id}",
        headers=owner_headers,
    ).status_code == 201

    response = client.post(
        "/chat",
        json={
            "message": "اشرح لينكس",
            "assistant_id": assistant["id"],
            "workspace_id": workspace_id,
        },
        headers=member_headers,
    )
    assert response.status_code == 200
    assert "[ASSISTANT INSTRUCTIONS]" in mock_reply.await_args.args[0]
    assert "استخدم أسلوبًا عمليًا." in mock_reply.await_args.args[0]


def test_non_member_cannot_view_or_use_shared_assistant(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    owner_token = _register_and_login(client, "shared-nonmember-owner@example.com")
    outsider_token = _register_and_login(client, "shared-nonmember-outsider@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace_id = _create_workspace(client, owner_token)

    assistant = client.post(
        "/assistants",
        json={"name": "Private Team", "instructions": "لا تُظهر هذا لغير الأعضاء."},
        headers=owner_headers,
    ).json()
    assert client.post(
        f"/assistants/{assistant['id']}/workspace-share/{workspace_id}",
        headers=owner_headers,
    ).status_code == 201

    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    assert client.get(
        f"/workspaces/{workspace_id}/shared-assistants",
        headers=outsider_headers,
    ).status_code == 404
    assert client.post(
        "/chat",
        json={
            "message": "حاول",
            "assistant_id": assistant["id"],
            "workspace_id": workspace_id,
        },
        headers=outsider_headers,
    ).status_code == 404


def test_non_owner_cannot_unshare_assistant(client):
    owner_token = _register_and_login(client, "unshare-owner@example.com")
    member_token = _register_and_login(client, "unshare-member@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    member_headers = {"Authorization": f"Bearer {member_token}"}
    workspace_id = _create_workspace(client, owner_token)
    assert client.post(
        f"/workspaces/{workspace_id}/members",
        json={"email": "unshare-member@example.com", "role": "member"},
        headers=owner_headers,
    ).status_code in {200, 201}
    assistant = client.post(
        "/assistants",
        json={"name": "Owner Only", "instructions": "صالح"},
        headers=owner_headers,
    ).json()
    assert client.post(
        f"/assistants/{assistant['id']}/workspace-share/{workspace_id}",
        headers=owner_headers,
    ).status_code == 201

    assert client.delete(
        f"/assistants/{assistant['id']}/workspace-share/{workspace_id}",
        headers=member_headers,
    ).status_code == 404
