"""اختبارات سجل تدقيق مساحات العمل."""
from unittest.mock import AsyncMock


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_workspace_activity_is_recorded_and_readable_by_manager(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.workspace_members.send_workspace_invitation_email",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.routers.workspace_members.secrets.token_urlsafe",
        lambda n: "D" * 40,
    )

    owner_token = _register_and_login(client, "audit-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    created = client.post(
        "/workspaces",
        json={"name": "Audit Team"},
        headers=owner_headers,
    )
    workspace = created.json()
    assert created.status_code == 201

    renamed = client.patch(
        f"/workspaces/{workspace['id']}",
        json={"name": "Audit Team 2"},
        headers=owner_headers,
    )
    assert renamed.status_code == 200

    _register_and_login(client, "audit-member@example.com")
    invited = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "audit-member@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invited.status_code == 201

    logs = client.get(
        f"/workspaces/{workspace['id']}/audit-logs",
        headers=owner_headers,
    )
    assert logs.status_code == 200
    events = [item["event_type"] for item in logs.json()]
    assert "workspace_created" in events
    assert "workspace_renamed" in events
    assert "workspace_invitation_created" in events


def test_non_manager_cannot_read_workspace_audit_log(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.workspace_members.send_workspace_invitation_email",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.routers.workspace_members.secrets.token_urlsafe",
        lambda n: "E" * 40,
    )

    owner_token = _register_and_login(client, "audit-owner-2@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Private Audit"},
        headers=owner_headers,
    ).json()

    member_token = _register_and_login(client, "audit-member-2@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}

    invite = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "audit-member-2@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invite.status_code == 201

    accepted = client.post(
        "/workspace-invitations/accept",
        json={"token": "E" * 40},
        headers=member_headers,
    )
    assert accepted.status_code == 200

    logs = client.get(
        f"/workspaces/{workspace['id']}/audit-logs",
        headers=member_headers,
    )
    assert logs.status_code == 403
