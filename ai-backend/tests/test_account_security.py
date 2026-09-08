"""
اختبارات المرحلة الثالثة: الحماية من Brute Force، تأكيد البريد، إعادة تعيين كلمة المرور
"""
from app.auth.cache import remember_email_verification_token, remember_password_reset_token
from app.auth.security import create_email_verification_token, create_password_reset_token, decode_token
from app.config import settings as app_settings
from app.models.user import User


def test_new_user_starts_unverified(client):
    response = client.post(
        "/auth/register", json={"email": "unverified@example.com", "password": "StrongPass123"}
    )
    assert response.json()["is_email_verified"] is False


def test_account_locks_after_max_failed_attempts(client, monkeypatch):
    monkeypatch.setattr(app_settings, "MAX_FAILED_LOGIN_ATTEMPTS", 3)
    client.post(
        "/auth/register", json={"email": "lockout@example.com", "password": "StrongPass123"}
    )

    for _ in range(3):
        response = client.post(
            "/auth/login", json={"email": "lockout@example.com", "password": "WrongPassword"}
        )
        assert response.status_code == 401

    locked_response = client.post(
        "/auth/login", json={"email": "lockout@example.com", "password": "StrongPass123"}
    )
    assert locked_response.status_code == 403


def test_successful_login_resets_failed_attempts(client, monkeypatch):
    monkeypatch.setattr(app_settings, "MAX_FAILED_LOGIN_ATTEMPTS", 3)
    client.post("/auth/register", json={"email": "reset@example.com", "password": "StrongPass123"})

    client.post("/auth/login", json={"email": "reset@example.com", "password": "WrongPassword"})
    client.post("/auth/login", json={"email": "reset@example.com", "password": "WrongPassword"})

    good_login = client.post(
        "/auth/login", json={"email": "reset@example.com", "password": "StrongPass123"}
    )
    assert good_login.status_code == 200

    client.post("/auth/login", json={"email": "reset@example.com", "password": "WrongPassword"})
    still_open = client.post(
        "/auth/login", json={"email": "reset@example.com", "password": "WrongPassword"}
    )
    assert still_open.status_code == 401


def test_confirm_email_verification(client, db_session):
    register_response = client.post(
        "/auth/register", json={"email": "confirm@example.com", "password": "StrongPass123"}
    )
    user_id = register_response.json()["id"]
    token = create_email_verification_token(user_id)
    payload = decode_token(token, expected_type="email_verification")
    assert payload and payload.get("jti")
    assert remember_email_verification_token(payload["jti"], 3600)

    response = client.post("/auth/verify-email/confirm", json={"token": token})
    assert response.status_code == 200

    user = db_session.query(User).filter(User.id == user_id).first()
    assert user.is_email_verified is True

    replay = client.post("/auth/verify-email/confirm", json={"token": token})
    assert replay.status_code == 400


def test_confirm_email_verification_rejects_bad_token(client):
    response = client.post("/auth/verify-email/confirm", json={"token": "not-a-real-token"})
    assert response.status_code == 400


def test_request_email_verification_requires_auth(client):
    response = client.post("/auth/verify-email/request")
    assert response.status_code == 401


def test_password_reset_request_never_reveals_if_email_exists(client):
    known = client.post(
        "/auth/password-reset/request", json={"email": "known@example.com"}
    )
    unknown = client.post(
        "/auth/password-reset/request", json={"email": "never_registered@example.com"}
    )
    assert known.status_code == 202
    assert unknown.status_code == 202
    assert known.json() == unknown.json()


def test_password_reset_confirm_changes_password(client, db_session):
    register_response = client.post(
        "/auth/register", json={"email": "forgot@example.com", "password": "OldPass123"}
    )
    user_id = register_response.json()["id"]
    token = create_password_reset_token(user_id)
    payload = decode_token(token, expected_type="password_reset")
    assert payload and payload.get("jti")
    assert remember_password_reset_token(payload["jti"], 3600)

    response = client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "NewPass123"}
    )
    assert response.status_code == 200

    old_login = client.post(
        "/auth/login", json={"email": "forgot@example.com", "password": "OldPass123"}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login", json={"email": "forgot@example.com", "password": "NewPass123"}
    )
    assert new_login.status_code == 200

    replay = client.post(
        "/auth/password-reset/confirm", json={"token": token, "new_password": "AnotherPass123"}
    )
    assert replay.status_code == 400


def test_password_reset_confirm_rejects_bad_token(client):
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": "NewPass123"},
    )
    assert response.status_code == 400
