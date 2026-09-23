"""اختبارات روابط المساعدين العامة ونسخها."""
def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _create_assistant(client, headers, name="Tutor"):
    response = client.post(
        "/assistants",
        json={
            "name": name,
            "description": "مساعد عام",
            "instructions": "تعليمات خاصة لا يجب أن تظهر في الصفحة العامة.",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_public_assistant_can_be_enabled_and_read_without_instructions(client):
    token = _register_and_login(client, "public-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assistant = _create_assistant(client, headers)

    settings_response = client.post(
        f"/assistants/{assistant['id']}/public",
        headers=headers,
    )
    assert settings_response.status_code == 200
    settings_payload = settings_response.json()
    assert settings_payload["is_public"] is True
    assert settings_payload["public_token"]
    assert "/public-assistant/" in settings_payload["public_url"]

    public_response = client.get(f"/public/assistants/{settings_payload['public_token']}")
    assert public_response.status_code == 200
    public_payload = public_response.json()
    assert public_payload["name"] == "Tutor"
    assert public_payload["description"] == "مساعد عام"
    assert "instructions" not in public_payload


def test_rotating_public_link_invalidates_old_token(client):
    token = _register_and_login(client, "public-rotate@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assistant = _create_assistant(client, headers)

    first = client.post(f"/assistants/{assistant['id']}/public", headers=headers).json()
    second = client.post(
        f"/assistants/{assistant['id']}/public/rotate",
        headers=headers,
    ).json()

    assert first["public_token"] != second["public_token"]
    assert client.get(f"/public/assistants/{first['public_token']}").status_code == 404
    assert client.get(f"/public/assistants/{second['public_token']}").status_code == 200


def test_disabling_public_link_makes_token_invalid(client):
    token = _register_and_login(client, "public-disable@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assistant = _create_assistant(client, headers)

    enabled = client.post(f"/assistants/{assistant['id']}/public", headers=headers).json()
    response = client.delete(f"/assistants/{assistant['id']}/public", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_public"] is False
    assert response.json()["public_token"] is None

    assert client.get(f"/public/assistants/{enabled['public_token']}").status_code == 404


def test_public_assistant_can_be_cloned_by_authenticated_user(client):
    owner_token = _register_and_login(client, "public-clone-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    assistant = _create_assistant(client, owner_headers, name="Research Helper")
    public = client.post(f"/assistants/{assistant['id']}/public", headers=owner_headers).json()

    clone_token = _register_and_login(client, "public-clone-user@example.com")
    clone_headers = {"Authorization": f"Bearer {clone_token}"}

    response = client.post(
        f"/public/assistants/{public['public_token']}/duplicate",
        headers=clone_headers,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"].startswith("Research Helper")
    clone_id = payload["conversation_assistant_id"]

    cloned = client.get("/assistants", headers=clone_headers).json()
    matches = [item for item in cloned if item["id"] == clone_id]
    assert len(matches) == 1
    assert matches[0]["is_public"] is False


def test_public_assistant_clone_requires_authentication(client):
    token = _register_and_login(client, "public-auth-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assistant = _create_assistant(client, headers)
    public = client.post(f"/assistants/{assistant['id']}/public", headers=headers).json()

    client.post("/auth/logout")

    assert client.post(
        f"/public/assistants/{public['public_token']}/duplicate",
    ).status_code == 401
