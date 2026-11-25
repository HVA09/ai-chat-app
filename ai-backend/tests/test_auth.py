"""
اختبارات مسارات المصادقة: تسجيل، دخول، تدوير الجلسات وحماية المسارات الخاصة
"""
from app.auth.security import create_access_token, decode_token
from app.config import settings as app_settings
from app.models.user import User


def test_register_new_user(client):
    response = client.post(
        "/auth/register", json={"email": "test@example.com", "password": "StrongPass123"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "test@example.com"
    assert "hashed_password" not in body


def test_register_duplicate_email_fails(client):
    client.post("/auth/register", json={"email": "dup@example.com", "password": "StrongPass123"})
    response = client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "AnotherPass123"}
    )
    assert response.status_code == 400


def test_register_rejects_short_password(client):
    response = client.post(
        "/auth/register", json={"email": "short@example.com", "password": "1234567"}
    )
    assert response.status_code == 422


def test_initial_admin_is_promoted_only_after_email_verification(client, monkeypatch, db_session):
    from app.auth import routes as auth_routes_module
    from app.models.user import UserRole

    monkeypatch.setattr(app_settings, "INITIAL_ADMIN_EMAIL", "first@example.com")
    verification_tokens = []
    monkeypatch.setattr(
        auth_routes_module,
        "send_verification_email",
        lambda recipient, token: verification_tokens.append(token),
    )
    response = client.post(
        "/auth/register", json={"email": "first@example.com", "password": "StrongPass123"}
    )
    assert response.status_code == 201
    assert response.json()["role"] == "user"
    user = db_session.query(User).filter(User.email == "first@example.com").one()
    assert user.role == UserRole.user
    assert len(verification_tokens) == 1

    verified = client.post(
        "/auth/verify-email/confirm",
        json={"token": verification_tokens[0]},
    )
    assert verified.status_code == 200
    db_session.refresh(user)
    assert user.is_email_verified is True
    assert user.role == UserRole.admin


def test_second_user_is_regular(client, monkeypatch):
    monkeypatch.setattr(app_settings, "INITIAL_ADMIN_EMAIL", "first@example.com")
    client.post("/auth/register", json={"email": "first@example.com", "password": "StrongPass123"})
    response = client.post(
        "/auth/register", json={"email": "second@example.com", "password": "StrongPass123"}
    )
    assert response.json()["role"] == "user"


def test_login_success_uses_httponly_cookies(client):
    client.post(
        "/auth/register", json={"email": "login@example.com", "password": "StrongPass123"}
    )
    response = client.post(
        "/auth/login", json={"email": "login@example.com", "password": "StrongPass123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert not body.get("access_token")
    assert not body.get("refresh_token")
    assert client.cookies.get("access_token")
    assert client.cookies.get("refresh_token")


def test_login_wrong_password_fails(client):
    client.post(
        "/auth/register", json={"email": "wrong@example.com", "password": "StrongPass123"}
    )
    response = client.post(
        "/auth/login", json={"email": "wrong@example.com", "password": "WrongPassword"}
    )
    assert response.status_code == 401


def test_protected_route_requires_token(client):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_refresh_fails_for_deactivated_user(client, db_session):
    client.post(
        "/auth/register", json={"email": "inactive@example.com", "password": "StrongPass123"}
    )
    login_response = client.post(
        "/auth/login", json={"email": "inactive@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code == 200

    user = db_session.query(User).filter(User.email == "inactive@example.com").first()
    user.is_active = False
    db_session.commit()

    response = client.post("/auth/refresh")
    assert response.status_code == 401


def test_refresh_requires_cookie_not_body(client):
    client.post(
        "/auth/register", json={"email": "cookie@example.com", "password": "StrongPass123"}
    )
    login_response = client.post(
        "/auth/login", json={"email": "cookie@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code == 200
    refresh_token = client.cookies.get("refresh_token")
    assert refresh_token
    client.cookies.clear()
    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


def test_login_rejects_inactive_user(client, db_session):
    client.post(
        "/auth/register", json={"email": "disabled@example.com", "password": "StrongPass123"}
    )
    user = db_session.query(User).filter(User.email == "disabled@example.com").first()
    user.is_active = False
    db_session.commit()

    response = client.post(
        "/auth/login", json={"email": "disabled@example.com", "password": "StrongPass123"}
    )
    assert response.status_code == 403


def test_register_rejects_weak_password_without_uppercase(client):
    response = client.post(
        "/auth/register", json={"email": "weak@example.com", "password": "weakpass123"}
    )
    assert response.status_code == 422


def test_login_normalizes_email_case(client):
    client.post(
        "/auth/register", json={"email": "CaseUser@Example.com", "password": "StrongPass123"}
    )
    response = client.post(
        "/auth/login", json={"email": "caseuser@example.com", "password": "StrongPass123"}
    )
    assert response.status_code == 200
    assert client.cookies.get("access_token")


def test_jwt_round_trip_uses_configured_algorithm():
    token = create_access_token(123, token_version=7, session_jti="test-session-jti")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "123"
    assert payload["type"] == "access"
    assert payload["ver"] == 7
    assert payload["jti"] == "test-session-jti"


def test_initial_admin_is_promoted_only_after_email_verification(
    client, db_session, monkeypatch
):
    from app.auth import routes as auth_routes

    monkeypatch.setattr(app_settings, "INITIAL_ADMIN_EMAIL", "first@example.com")
    monkeypatch.setattr(auth_routes, "remember_email_verification_token", lambda *_: True)
    captured = {}
    monkeypatch.setattr(
        auth_routes,
        "send_verification_email",
        lambda email, token: captured.update(email=email, token=token),
    )
    response = client.post(
        "/auth/register",
        json={"email": "first@example.com", "password": "StrongPass123"},
    )
    assert response.status_code == 201
    user = db_session.query(User).filter_by(email="first@example.com").one()
    assert user.role == "user"
    assert user.is_email_verified is False

    monkeypatch.setattr(auth_routes, "consume_email_verification_token", lambda _jti: True)
    confirmed = client.post(
        "/auth/verify-email/confirm",
        json={"token": captured["token"]},
    )
    assert confirmed.status_code == 200
    db_session.refresh(user)
    assert user.is_email_verified is True
    assert user.role == "admin"
