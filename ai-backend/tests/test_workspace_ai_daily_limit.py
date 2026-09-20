"""اختبارات حد طلبات AI اليومي لمساحة العمل."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.models.usage_log import UsageLog
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_owner_can_set_and_clear_workspace_daily_limit(client):
    token = _register_and_login(client, "quota-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Quota Workspace"},
        headers=headers,
    ).json()

    response = client.patch(
        f"/workspaces/{workspace['id']}/limit",
        json={"daily_ai_request_limit": 12},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["daily_ai_request_limit"] == 12

    response = client.patch(
        f"/workspaces/{workspace['id']}/limit",
        json={"daily_ai_request_limit": None},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["daily_ai_request_limit"] is None


def test_member_cannot_change_workspace_daily_limit(client, db_session):
    owner_token = _register_and_login(client, "quota-owner-2@example.com")
    owner = client.get("/users/me", headers={"Authorization": f"Bearer {owner_token}"}).json()
    member_token = _register_and_login(client, "quota-member@example.com")
    member = client.get("/users/me", headers={"Authorization": f"Bearer {member_token}"}).json()

    workspace = Workspace(owner_id=owner["id"], name="Restricted Quota")
    db_session.add(workspace)
    db_session.flush()
    db_session.add_all(
        [
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=owner["id"],
                role=WorkspaceRole.owner,
            ),
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=member["id"],
                role=WorkspaceRole.member,
            ),
        ]
    )
    db_session.commit()

    response = client.patch(
        f"/workspaces/{workspace.id}/limit",
        json={"daily_ai_request_limit": 5},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert response.status_code == 403


def test_workspace_daily_limit_blocks_ai_requests_but_ignores_other_workspaces(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="لن يجب أن يصل الطلب إلى المزود")),
    )

    token = _register_and_login(client, "quota-enforcement@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspaces = client.get("/workspaces", headers=headers).json()
    personal_workspace = next(item for item in workspaces if item["name"] == "Personal")

    quota_workspace = client.post(
        "/workspaces",
        json={"name": "Quota"},
        headers=headers,
    ).json()
    other_workspace = client.post(
        "/workspaces",
        json={"name": "Other"},
        headers=headers,
    ).json()

    response = client.patch(
        f"/workspaces/{quota_workspace['id']}/limit",
        json={"daily_ai_request_limit": 2},
        headers=headers,
    )
    assert response.status_code == 200

    user = client.get("/users/me", headers=headers).json()
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            UsageLog(
                user_id=user["id"],
                workspace_id=quota_workspace["id"],
                endpoint="/chat",
                created_at=now - timedelta(hours=1),
            ),
            UsageLog(
                user_id=user["id"],
                workspace_id=quota_workspace["id"],
                endpoint="/chat",
                created_at=now - timedelta(hours=2),
            ),
            UsageLog(
                user_id=user["id"],
                workspace_id=quota_workspace["id"],
                endpoint="/chat",
                created_at=now - timedelta(hours=30),
            ),
            UsageLog(
                user_id=user["id"],
                workspace_id=other_workspace["id"],
                endpoint="/chat",
                created_at=now - timedelta(hours=1),
            ),
            UsageLog(
                user_id=user["id"],
                workspace_id=personal_workspace["id"],
                endpoint="/chat",
                created_at=now - timedelta(hours=1),
            ),
        ]
    )
    db_session.commit()

    blocked = client.post(
        "/chat",
        json={"message": "يجب أن يُحظر", "workspace_id": quota_workspace["id"]},
        headers=headers,
    )
    assert blocked.status_code == 429
    assert "حد مساحة العمل" in blocked.json()["detail"]
    chat_router_module.get_ai_reply.assert_not_awaited()

    allowed = client.post(
        "/chat",
        json={"message": "مساحة أخرى", "workspace_id": other_workspace["id"]},
        headers=headers,
    )
    assert allowed.status_code == 200
    assert chat_router_module.get_ai_reply.await_count == 1


def test_workspace_daily_limit_rejects_invalid_values(client):
    token = _register_and_login(client, "quota-validation@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Validation"},
        headers=headers,
    ).json()

    for value in [0, -1]:
        response = client.patch(
            f"/workspaces/{workspace['id']}/limit",
            json={"daily_ai_request_limit": value},
            headers=headers,
        )
        assert response.status_code == 422
