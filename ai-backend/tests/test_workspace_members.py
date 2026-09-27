from unittest.mock import AsyncMock


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_invite_accept_and_manage_member(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.workspace_members.send_workspace_invitation_email",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.routers.workspace_members.secrets.token_urlsafe",
        lambda n: "A" * 40,
    )

    owner_token = _register_and_login(client, "owner-members@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Team"},
        headers=owner_headers,
    ).json()

    member_token = _register_and_login(client, "member@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}

    invite = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "member@example.com", "role": "admin"},
        headers=owner_headers,
    )
    assert invite.status_code == 201

    accepted = client.post(
        "/workspace-invitations/accept",
        json={"token": "A" * 40},
        headers=member_headers,
    )
    assert accepted.status_code == 200
    assert accepted.json()["role"] == "admin"

    members = client.get(
        f"/workspaces/{workspace['id']}/members",
        headers=owner_headers,
    )
    member = next(
        item for item in members.json() if item["email"] == "member@example.com"
    )

    changed = client.patch(
        f"/workspaces/{workspace['id']}/members/{member['id']}/role",
        json={"role": "member"},
        headers=owner_headers,
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "member"

    removed = client.delete(
        f"/workspaces/{workspace['id']}/members/{member['id']}",
        headers=owner_headers,
    )
    assert removed.status_code == 204


def test_invitation_belongs_to_invited_account(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.workspace_members.send_workspace_invitation_email",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.routers.workspace_members.secrets.token_urlsafe",
        lambda n: "B" * 40,
    )

    owner_token = _register_and_login(client, "owner-token@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Private"},
        headers=owner_headers,
    ).json()

    _register_and_login(client, "invited@example.com")
    other_token = _register_and_login(client, "other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    created = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "invited@example.com"},
        headers=owner_headers,
    )
    assert created.status_code == 201

    accepted = client.post(
        "/workspace-invitations/accept",
        json={"token": "B" * 40},
        headers=other_headers,
    )
    assert accepted.status_code == 403


def test_duplicate_pending_invitation_rejected(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.workspace_members.send_workspace_invitation_email",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.routers.workspace_members.secrets.token_urlsafe",
        lambda n: "C" * 40,
    )

    owner_token = _register_and_login(client, "owner-dup@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "Dup"},
        headers=owner_headers,
    ).json()

    _register_and_login(client, "target-dup@example.com")

    first = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "target-dup@example.com"},
        headers=owner_headers,
    )
    assert first.status_code == 201

    duplicate = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "target-dup@example.com"},
        headers=owner_headers,
    )
    assert duplicate.status_code == 409


def test_enterprise_rbac_custom_role_controls_member_operations(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.workspace_members.send_workspace_invitation_email",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.routers.workspace_members.secrets.token_urlsafe",
        lambda n: "R" * 40,
    )

    owner_token = _register_and_login(client, "rbac-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "RBAC Team"},
        headers=owner_headers,
    ).json()

    member_token = _register_and_login(client, "rbac-member@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}

    invite_member = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "rbac-member@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invite_member.status_code == 201

    accepted = client.post(
        "/workspace-invitations/accept",
        json={"token": "R" * 40},
        headers=member_headers,
    )
    assert accepted.status_code == 200

    role = client.post(
        f"/workspaces/{workspace['id']}/rbac/roles",
        json={
            "name": "Inviter",
            "description": "Can read members and send invites",
            "permissions": ["members.read", "members.invite"],
        },
        headers=owner_headers,
    )
    assert role.status_code == 201
    role_id = role.json()["id"]

    assigned = client.patch(
        f"/workspaces/{workspace['id']}/members/2/rbac-role",
        json={"rbac_role_id": role_id},
        headers=owner_headers,
    )
    assert assigned.status_code == 200
    assert assigned.json()["id"] == role_id

    forbidden_rbac = client.post(
        f"/workspaces/{workspace['id']}/rbac/roles",
        json={
            "name": "Escalation",
            "permissions": ["rbac.manage"],
        },
        headers=member_headers,
    )
    assert forbidden_rbac.status_code == 403

    third_token = _register_and_login(client, "rbac-third@example.com")
    assert third_token

    invitation = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "rbac-third@example.com", "role": "member"},
        headers=member_headers,
    )
    assert invitation.status_code == 201

    members = client.get(
        f"/workspaces/{workspace['id']}/members",
        headers=member_headers,
    )
    assert members.status_code == 200
    assert any(item["email"] == "rbac-member@example.com" for item in members.json())

    cannot_remove = client.delete(
        f"/workspaces/{workspace['id']}/members/3",
        headers=member_headers,
    )
    assert cannot_remove.status_code == 403


def test_enterprise_rbac_role_cannot_grant_permissions_beyond_creator(client):
    owner_token = _register_and_login(client, "rbac-limit-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = client.post(
        "/workspaces",
        json={"name": "RBAC Limit"},
        headers=owner_headers,
    ).json()

    role = client.post(
        f"/workspaces/{workspace['id']}/rbac/roles",
        json={
            "name": "Full Role",
            "permissions": ["rbac.manage", "billing.manage"],
        },
        headers=owner_headers,
    )
    assert role.status_code == 201

    member_token = _register_and_login(client, "rbac-limit-member@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}

    invite = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "rbac-limit-member@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invite.status_code == 201

    accepted = client.post(
        "/workspace-invitations/accept",
        json={"token": "D" * 40},
        headers=member_headers,
    )
    assert accepted.status_code in {404, 410}
