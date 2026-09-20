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


def test_member_cannot_change_workspace_daily_limit(client):
    owner_token = _register_and_login(client, "quota-owner-2@example.com")
    owner = client.get("/users/me", headers={"Authorization": f"Bearer {owner_token}"}).json()
    member_token = _register_and_login(client, "quota-member@example.com")
    member = client.get("/users/me", headers={"Authorization": f"Bearer {member_token}"}).json()

    workspace = Workspace(owner_id=owner["id"], name="Restricted Quota")
    db = client.app.dependency_overrides
