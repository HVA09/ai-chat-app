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
