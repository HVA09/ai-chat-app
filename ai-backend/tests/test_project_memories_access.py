"""اختبارات عزل ذاكرة المشاريع بين المستخدمين."""
def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _create_workspace(client, headers, name):
    response = client.post("/workspaces", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def _create_project(client, headers, workspace_id, name="Private"):
    response = client.post(
        "/projects",
        json={"workspace_id": workspace_id, "name": name},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_other_user_cannot_read_or_manage_project_memory(client):
    token_a = _register_and_login(client, "project-memory-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    workspace = _create_workspace(client, headers_a, "Private")
    project = _create_project(client, headers_a, workspace["id"])

    created = client.post(
        f"/projects/{project['id']}/memories",
        json={"content": "Secret project memory"},
        headers=headers_a,
    )
    assert created.status_code == 201
    memory_id = created.json()["id"]

    token_b = _register_and_login(client, "project-memory-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.get(
        f"/projects/{project['id']}/memories",
        headers=headers_b,
    ).status_code == 404

    assert client.post(
        f"/projects/{project['id']}/memories",
        json={"content": "Hijack"},
        headers=headers_b,
    ).status_code == 404

    assert client.patch(
        f"/projects/{project['id']}/memories/{memory_id}",
        json={"content": "Hijack"},
        headers=headers_b,
    ).status_code == 404

    assert client.delete(
        f"/projects/{project['id']}/memories/{memory_id}",
        headers=headers_b,
    ).status_code == 404


def test_project_memory_is_shared_with_workspace_member_but_not_external_user(client):
    owner_token = _register_and_login(client, "project-memory-shared-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _create_workspace(client, owner_headers, "Shared")
    project = _create_project(client, owner_headers, workspace["id"])

    created = client.post(
        f"/projects/{project['id']}/memories",
        json={"content": "Shared workspace fact"},
        headers=owner_headers,
    )
    assert created.status_code == 201

    member_token = _register_and_login(client, "project-memory-member@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}
    invite = client.post(
        f"/workspaces/{workspace['id']}/invitations",
        json={"email": "project-memory-member@example.com", "role": "member"},
        headers=owner_headers,
    )
    assert invite.status_code == 201

    invitation = client.get("/workspace-invitations", headers=member_headers)
    assert invitation.status_code == 200
    token = invitation.json()[0]["token"]

    accepted = client.post(
        "/workspace-invitations/accept",
        json={"token": token},
        headers=member_headers,
    )
    assert accepted.status_code == 200

    listed = client.get(
        f"/projects/{project['id']}/memories",
        headers=member_headers,
    )
    assert listed.status_code == 200
    assert [item["content"] for item in listed.json()] == ["Shared workspace fact"]

    external_token = _register_and_login(client, "project-memory-external@example.com")
    external_headers = {"Authorization": f"Bearer {external_token}"}
    assert client.get(
        f"/projects/{project['id']}/memories",
        headers=external_headers,
    ).status_code == 404
