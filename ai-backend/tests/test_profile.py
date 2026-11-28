"""
اختبارات المرحلة الرابعة: الملف الشخصي، تغيير كلمة المرور، حذف الحساب
"""


def _register_and_login(client, email="profile@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_get_me_includes_profile_fields(client):
    token = _register_and_login(client)
    body = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert body["full_name"] is None
    assert body["avatar_url"] is None
    assert body["is_2fa_enabled"] is False


def test_update_profile(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch("/users/me", json={"full_name": "محمد", "avatar_url": "https://example.com/avatar.png"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "محمد"
    assert response.json()["avatar_url"] == "https://example.com/avatar.png"


def test_update_profile_partial_leaves_other_field_untouched(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.patch("/users/me", json={"full_name": "محمد"}, headers=headers)
    response = client.patch("/users/me", json={"avatar_url": "https://example.com/a.png"}, headers=headers)
    assert response.json()["full_name"] == "محمد"
    assert response.json()["avatar_url"] == "https://example.com/a.png"


def test_change_password_requires_correct_current_password(client):
    token = _register_and_login(client)
    response = client.post("/users/me/change-password", json={"current_password": "WrongOne123", "new_password": "NewPass123"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_change_password_success_revokes_existing_sessions_and_allows_new_login(client, db_session):
    from app.models.user import User
    from app.models.user_session import UserSession

    token = _register_and_login(client, "changepw@example.com", "OldPass123")
    response = client.post("/users/me/change-password", json={"current_password": "OldPass123", "new_password": "NewPass123"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    # The access token issued before the password change must stop working.
    stale_access = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert stale_access.status_code == 401
    # The refresh token from the same session must also be rejected.
    stale_refresh = client.post("/auth/refresh")
    assert stale_refresh.status_code == 401

    user = db_session.query(User).filter(User.email == "changepw@example.com").first()
    assert user.token_version == 1
    sessions = db_session.query(UserSession).filter(UserSession.user_id == user.id).all()
    assert sessions
    assert all(session.revoked_at is not None for session in sessions)

    old_login = client.post("/auth/login", json={"email": "changepw@example.com", "password": "OldPass123"})
    assert old_login.status_code == 401
    new_login = client.post("/auth/login", json={"email": "changepw@example.com", "password": "NewPass123"})
    assert new_login.status_code == 200


def test_delete_account_requires_correct_password(client):
    token = _register_and_login(client)
    response = client.request("DELETE", "/users/me", json={"password": "WrongPassword"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_delete_account_finishes_db_retention_before_storage(client, monkeypatch):
    from app.routers import users as users_router_module

    events = []
    monkeypatch.setattr(
        users_router_module,
        "privatize_account_workspace_attachments",
        lambda _db, user_id: events.append(("retention", user_id)),
    )
    monkeypatch.setattr(
        users_router_module,
        "enqueue_user_storage_cleanup",
        lambda _db, user_id: events.append(("outbox", user_id)),
    )
    monkeypatch.setattr(
        users_router_module,
        "dispatch_storage_cleanup",
        lambda: events.append(("dispatch", None)),
    )

    token = _register_and_login(client, "ordered-self-delete@example.com")
    response = client.request(
        "DELETE",
        "/users/me",
        json={"password": "StrongPass123"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    assert [event[0] for event in events] == ["retention", "outbox", "dispatch"]
    assert events[0][1] == events[1][1]


def test_delete_account_success(client):
    token = _register_and_login(client, "deleteme@example.com", "StrongPass123")
    response = client.request("DELETE", "/users/me", json={"password": "StrongPass123"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 204
    login_response = client.post("/auth/login", json={"email": "deleteme@example.com", "password": "StrongPass123"})
    assert login_response.status_code == 401


def test_profile_endpoints_require_authentication(client):
    assert client.patch("/users/me", json={"full_name": "x"}).status_code == 401
    assert client.post("/users/me/change-password", json={"current_password": "a", "new_password": "bbbbbbbb"}).status_code == 401


def test_export_account_data_contains_user_and_conversations_without_secrets(client, monkeypatch):
    from unittest.mock import AsyncMock

    from app.routers import chat as chat_router_module
    from app.services.ai_providers.base import AIReply

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تجريبي")),
    )
    token = _register_and_login(client, "export@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    client.patch(
        "/users/me",
        json={"full_name": "مستخدم التصدير", "avatar_url": "https://example.com/a.png"},
        headers=headers,
    )
    client.post("/chat", json={"message": "رسالة خاصة"}, headers=headers)

    response = client.get("/users/me/export", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]

    payload = response.json()
    assert payload["user"]["email"] == "export@example.com"
    assert payload["user"]["full_name"] == "مستخدم التصدير"
    assert payload["conversations"][0]["messages"][0]["content"] == "رسالة خاصة"
    assert "hashed_password" not in payload["user"]
    assert "totp_secret" not in payload["user"]



def test_account_export_rejects_data_over_preflight_record_limit(client, monkeypatch):
    from app.routers import users as users_router_module

    token = _register_and_login(client, "export-limit@example.com")
    monkeypatch.setattr(users_router_module, "MAX_ACCOUNT_EXPORT_RECORDS", 0)
    response = client.get(
        "/users/me/export",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 413
