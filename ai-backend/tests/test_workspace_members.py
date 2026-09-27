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
    token_values = iter(["R" * 40, "S" * 40])
    token_value = {"value": next(token_values)}
    monkeypatch.setattr(
        "app.routers.workspace_members.send_workspace_invitation_email",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.routers.workspace_members.secrets.token_urlsafe",
        lambda n: token_value["value"],
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
    third_token = _register_and_login(client, "rbac-third@example.com")
    third_headers = {"Authorization": f"Bearer {third_token}"}

    invite_member = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "rbac-member@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invite_member.status_code == 201

    accepted = client.post(
        "/workspace-invitations/accept",
        json={"token": token_value["value"]},
        headers=member_headers,
    )
    assert accepted.status_code == 200

    token_value["value"] = next(token_values)
    invite_third = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "rbac-third@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invite_third.status_code == 201

    accepted_third = client.post(
        "/workspace-invitations/accept",
        json={"token": token_value["value"]},
        headers=third_headers,
    )
    assert accepted_third.status_code == 200

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

    members = client.get(
        f"/workspaces/{workspace['id']}/members",
        headers=owner_headers,
    )
    assert members.status_code == 200
    member_by_email = {
        item["email"]: item["id"]
        for item in members.json()
    }

    assigned = client.patch(
        f"/workspaces/{workspace['id']}/members/{member_by_email['rbac-member@example.com']}/rbac-role",
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

    fourth_token = _register_and_login(client, "rbac-fourth@example.com")
    assert fourth_token

    token_value["value"] = next(token_values)
    invitation = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "rbac-fourth@example.com", "role": "member"},
        headers=member_headers,
    )
    assert invitation.status_code == 201

    cannot_remove = client.delete(
        f"/workspaces/{workspace['id']}/members/{member_by_email['rbac-third@example.com']}",
        headers=member_headers,
    )
    assert cannot_remove.status_code == 403
