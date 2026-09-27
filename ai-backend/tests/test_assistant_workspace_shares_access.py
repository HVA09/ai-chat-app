"""اختبارات عزل مشاركة المساعدين داخل مساحات العمل."""
def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_external_user_cannot_list_share_or_unshare_assistant_workspace_share(client):
    owner_token = _register_and_login(client, "assistant-share-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    workspace = client.post(
        "/workspaces",
        json={"name": "Private"},
        headers=owner_headers,
    ).json()
    assistant = client.post(
        "/assistants",
        json={"name": "Private Assistant", "instructions": "Private"},
        headers=owner_headers,
    ).json()

    shared = client.post(
        f"/assistants/{assistant['id']}/workspace-share/{workspace['id']}",
        headers=owner_headers,
    )
    assert shared.status_code == 201

    other_token = _register_and_login(client, "assistant-share-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    assert client.get(
        f"/workspaces/{workspace['id']}/shared-assistants",
        headers=other_headers,
    ).status_code == 404

    assert client.post(
        f"/assistants/{assistant['id']}/workspace-share/{workspace['id']}",
        headers=other_headers,
    ).status_code == 404

    assert client.delete(
        f"/assistants/{assistant['id']}/workspace-share/{workspace['id']}",
        headers=other_headers,
    ).status_code == 404

    # Owner can still remove the share.
    removed = client.delete(
        f"/assistants/{assistant['id']}/workspace-share/{workspace['id']}",
        headers=owner_headers,
    )
    assert removed.status_code == 204
