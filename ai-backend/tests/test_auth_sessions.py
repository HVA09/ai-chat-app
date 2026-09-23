"""اختبارات إدارة جلسات تسجيل الدخول."""
from datetime import datetime, timezone


def _register_and_login(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_login_creates_session_and_lists_current_session(client):
    token = _register_and_login(client, "sessions-list@example.com")
    response = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 1
    assert sessions[0]["is_current"] is True
    assert sessions[0]["user_agent"]
    assert sessions[0]["expires_at"]


def test_second_login_creates_a_second_session(client):
    token = _register_and_login(client, "sessions-two@example.com")
    first_cookie = client.cookies.get("refresh_token")
    response = client.post(
        "/auth/login",
        json={"email": "sessions-two@example.com", "password": "StrongPass123"},
        headers={"User-Agent": "Android Test Browser"},
    )
    assert response.status_code == 200
    assert client.cookies.get("refresh_token") != first_cookie

    sessions = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert len(sessions) == 2
    assert sum(1 for item in sessions if item["is_current"]) == 1
    assert any(item["user_agent"] == "Android Test Browser" for item in sessions)


def test_revoke_other_session(client):
    token = _register_and_login(client, "sessions-revoke@example.com")
    first_refresh = client.cookies.get("refresh_token")

    second = client.post(
        "/auth/login",
        json={"email": "sessions-revoke@example.com", "password": "StrongPass123"},
        headers={"User-Agent": "Second Browser"},
    )
    assert second.status_code == 200

    current_token = client.cookies.get("access_token")
    sessions = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {current_token}"},
    ).json()
    other = next(item for item in sessions if not item["is_current"])

    revoked = client.delete(
        f"/auth/sessions/{other['id']}",
        headers={"Authorization": f"Bearer {current_token}"},
    )
    assert revoked.status_code == 204

    remaining = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {current_token}"},
    ).json()
    assert len(remaining) == 1
    assert remaining[0]["is_current"] is True


def test_revoke_current_session_prevents_refresh(client):
    token = _register_and_login(client, "sessions-current@example.com")
    current_refresh = client.cookies.get("refresh_token")
    current_token = client.cookies.get("access_token")

    sessions = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {current_token}"},
    ).json()
    current = next(item for item in sessions if item["is_current"])

    revoked = client.delete(
        f"/auth/sessions/{current['id']}",
        headers={"Authorization": f"Bearer {current_token}"},
    )
    assert revoked.status_code == 204

    client.cookies.set("refresh_token", current_refresh)
    refresh_response = client.post("/auth/refresh")
    assert refresh_response.status_code == 401


def test_revoke_all_sessions_invalidates_current_access_token(client):
    token = _register_and_login(client, "sessions-all@example.com")
    response = client.post(
        "/auth/sessions/revoke-all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    protected = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert protected.status_code == 401

    client.cookies.delete("refresh_token")
    client.cookies.delete("access_token")


def test_expired_sessions_are_not_listed(client, db_session):
    token = _register_and_login(client, "sessions-expired@example.com")
    response = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    session_id = response.json()[0]["id"]

    from app.models.user_session import UserSession

    db_session.get(UserSession, session_id).expires_at = datetime.now(timezone.utc)
    db_session.flush()

    listed = client.get(
        "/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    assert listed.json() == []
