"""اختبارات مكتبة الموجهات المحفوظة."""
def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return client.cookies.get("access_token")


def test_saved_prompt_crud(client):
    token = _register_and_login(client, "saved-prompts@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/saved-prompts",
        json={"name": "تلخيص", "content": "لخص النص التالي في 5 نقاط."},
        headers=headers,
    )
    assert created.status_code == 201
    prompt = created.json()
    assert prompt["name"] == "تلخيص"
    assert prompt["content"] == "لخص النص التالي في 5 نقاط."

    listed = client.get("/saved-prompts", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [prompt["id"]]

    updated = client.patch(
        f"/saved-prompts/{prompt['id']}",
        json={"name": "تلخيص سريع", "content": "لخص النص في 3 نقاط."},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "تلخيص سريع"
    assert updated.json()["content"] == "لخص النص في 3 نقاط."

    deleted = client.delete(
        f"/saved-prompts/{prompt['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204
    assert client.get("/saved-prompts", headers=headers).json() == []


def test_saved_prompt_duplicate_name_case_insensitive(client):
    token = _register_and_login(client, "saved-prompts-dup@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post(
        "/saved-prompts",
        json={"name": "Research", "content": "Analyze carefully."},
        headers=headers,
    ).status_code == 201
    duplicate = client.post(
        "/saved-prompts",
        json={"name": " research ", "content": "Another prompt."},
        headers=headers,
    )
    assert duplicate.status_code == 409


def test_saved_prompt_is_private_per_user(client):
    token_a = _register_and_login(client, "saved-prompts-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    prompt = client.post(
        "/saved-prompts",
        json={"name": "Private", "content": "Secret instructions."},
        headers=headers_a,
    ).json()

    token_b = _register_and_login(client, "saved-prompts-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.get("/saved-prompts", headers=headers_b).json() == []
    assert client.patch(
        f"/saved-prompts/{prompt['id']}",
        json={"name": "Hijacked", "content": "x"},
        headers=headers_b,
    ).status_code == 404
    assert client.delete(
        f"/saved-prompts/{prompt['id']}",
        headers=headers_b,
    ).status_code == 404


def test_saved_prompts_require_authentication(client):
    assert client.get("/saved-prompts").status_code == 401



def test_saved_prompt_version_history_compare_and_restore(client):
    token = _register_and_login(client, "saved-prompts-versions@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/saved-prompts",
        json={"name": "Research", "content": "Analyze carefully."},
        headers=headers,
    )
    assert created.status_code == 201
    prompt = created.json()

    versions = client.get(
        f"/saved-prompts/{prompt['id']}/versions",
        headers=headers,
    )
    assert versions.status_code == 200
    assert len(versions.json()) == 1
    assert versions.json()[0]["version"] == 1
    assert versions.json()[0]["content"] == "Analyze carefully."

    updated = client.patch(
        f"/saved-prompts/{prompt['id']}",
        json={"name": "Research Updated", "content": "Analyze carefully and cite sources."},
        headers=headers,
    )
    assert updated.status_code == 200

    compared = client.get(
        f"/saved-prompts/{prompt['id']}/versions/1/compare-current",
        headers=headers,
    )
    assert compared.status_code == 200
    assert compared.json()["from_version"] == 1
    assert compared.json()["current_version"] == 2
    assert compared.json()["changed"] is True
    assert "-Analyze carefully." in compared.json()["diff"]
    assert "+Analyze carefully and cite sources." in compared.json()["diff"]

    restored = client.post(
        f"/saved-prompts/{prompt['id']}/versions/1/restore",
        headers=headers,
    )
    assert restored.status_code == 200
    assert restored.json()["name"] == "Research"
    assert restored.json()["content"] == "Analyze carefully."

    versions = client.get(
        f"/saved-prompts/{prompt['id']}/versions",
        headers=headers,
    )
    assert [item["version"] for item in versions.json()] == [3, 2, 1]


def test_saved_prompt_versions_are_private_to_owner(client):
    token_a = _register_and_login(client, "saved-prompts-version-owner@example.com")
    prompt = client.post(
        "/saved-prompts",
        json={"name": "Private", "content": "Secret prompt."},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()

    token_b = _register_and_login(client, "saved-prompts-version-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.get(
        f"/saved-prompts/{prompt['id']}/versions",
        headers=headers_b,
    ).status_code == 404
    assert client.get(
        f"/saved-prompts/{prompt['id']}/versions/1/compare-current",
        headers=headers_b,
    ).status_code == 404
    assert client.post(
        f"/saved-prompts/{prompt['id']}/versions/1/restore",
        headers=headers_b,
    ).status_code == 404
