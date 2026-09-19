"""اختبارات الذاكرة الدائمة للمستخدم."""
def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_memory_crud_and_user_scoping(client):
    token = _register_and_login(client, "memory-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/memories",
        json={"content": "أفضل الإجابات المختصرة مع أمثلة عملية."},
        headers=headers,
    )
    assert created.status_code == 201
    memory = created.json()
    assert memory["content"].startswith("أفضل الإجابات")

    updated = client.patch(
        f"/memories/{memory['id']}",
        json={"content": "أفضل الشرح بالعربية مع أمثلة عملية."},
        headers=headers,
    )
    assert updated.status_code == 200
    assert "بالعربية" in updated.json()["content"]

    listed = client.get("/memories", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == memory["id"]

    other = _register_and_login(client, "memory-other@example.com")
    other_headers = {"Authorization": f"Bearer {other}"}
    assert client.patch(
        f"/memories/{memory['id']}",
        json={"content": "اختراق"},
        headers=other_headers,
    ).status_code == 404
    assert client.delete(
        f"/memories/{memory['id']}",
        headers=other_headers,
    ).status_code == 404

    assert client.delete(f"/memories/{memory['id']}", headers=headers).status_code == 204
    assert client.get("/memories", headers=headers).json() == []


def test_memory_rejects_blank_content(client):
    token = _register_and_login(client, "memory-validation@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/memories",
        json={"content": "   "},
        headers=headers,
    )
    assert response.status_code == 422
