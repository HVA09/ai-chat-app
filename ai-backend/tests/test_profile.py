"""
اختبارات المرحلة الرابعة: الملف الشخصي، تغيير كلمة المرور، حذف الحساب
"""


def _register_and_login(client, email="profile@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.json()["access_token"]


def test_get_me_includes_profile_fields(client):
    token = _register_and_login(client)
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    body = response.json()
    assert body["full_name"] is None
    assert body["avatar_url"] is None
    assert body["is_2fa_enabled"] is False


def test_update_profile(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch(
        "/users/me",
        json={"full_name": "محمد", "avatar_url": "https://example.com/avatar.png"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "محمد"
    assert body["avatar_url"] == "https://example.com/avatar.png"


def test_update_profile_partial_leaves_other_field_untouched(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.patch("/users/me", json={"full_name": "محمد"}, headers=headers)

    response = client.patch(
        "/users/me", json={"avatar_url": "https://example.com/a.png"}, headers=headers
    )
    assert response.json()["full_name"] == "محمد"
    assert response.json()["avatar_url"] == "https://example.com/a.png"


def test_change_password_requires_correct_current_password(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/users/me/change-password",
        json={"current_password": "WrongOne123", "new_password": "NewPass123"},
        headers=headers,
    )
    assert response.status_code == 401


def test_change_password_success_allows_login_with_new_password(client):
    token = _register_and_login(client, "changepw@example.com", "OldPass123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/users/me/change-password",
        json={"current_password": "OldPass123", "new_password": "NewPass123"},
        headers=headers,
    )
    assert response.status_code == 200

    old_login = client.post(
        "/auth/login", json={"email": "changepw@example.com", "password": "OldPass123"}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login", json={"email": "changepw@example.com", "password": "NewPass123"}
    )
    assert new_login.status_code == 200


def test_delete_account_requires_correct_password(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.request(
        "DELETE", "/users/me", json={"password": "WrongPassword"}, headers=headers
    )
    assert response.status_code == 401


def test_delete_account_success(client):
    token = _register_and_login(client, "deleteme@example.com", "StrongPass123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.request(
        "DELETE", "/users/me", json={"password": "StrongPass123"}, headers=headers
    )
    assert response.status_code == 204

    login_response = client.post(
        "/auth/login", json={"email": "deleteme@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code == 401


def test_profile_endpoints_require_authentication(client):
    assert client.patch("/users/me", json={"full_name": "x"}).status_code == 401
    assert (
        client.post(
            "/users/me/change-password",
            json={"current_password": "a", "new_password": "bbbbbbbb"},
        ).status_code
        == 401
    )
