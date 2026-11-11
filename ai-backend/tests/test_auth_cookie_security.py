"""Cross-site cookie and CSRF regression tests for hosted environments."""

from fastapi import Response

from app.auth.routes import _set_session_cookies
from app.config import settings


def test_staging_auth_cookies_are_secure_and_cross_site_compatible(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    response = Response()

    _set_session_cookies(response, "access-test-token", "refresh-test-token")

    cookies = response.headers.getlist("set-cookie")
    assert len(cookies) == 2
    for cookie in cookies:
        lowered = cookie.lower()
        assert "httponly" in lowered
        assert "secure" in lowered
        assert "samesite=none" in lowered
    assert any(cookie.startswith("access_token=") and "path=/" in cookie.lower() for cookie in cookies)
    assert any(cookie.startswith("refresh_token=") and "path=/auth" in cookie.lower() for cookie in cookies)


def test_staging_rejects_untrusted_cookie_authenticated_mutations(client, monkeypatch):
    email = "staging-csrf@example.com"
    password = "StrongPass123"
    registered = client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )
    assert registered.status_code == 201

    logged_in = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert logged_in.status_code == 200
    assert client.cookies.get("access_token")
    assert client.cookies.get("refresh_token")

    stage_origin = "https://ai-chat-stage-frontend.onrender.com"
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "CORS_ORIGINS", [stage_origin])

    blocked = client.post(
        "/auth/logout",
        headers={"Origin": "https://untrusted.example"},
    )
    assert blocked.status_code == 403

    # The rejected cross-site request must not revoke the still-valid session.
    still_authenticated = client.get("/users/me")
    assert still_authenticated.status_code == 200

    allowed = client.post(
        "/auth/logout",
        headers={"Origin": stage_origin},
    )
    assert allowed.status_code == 204
