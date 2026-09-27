import asyncio
from urllib.parse import parse_qs, urlparse

import pytest

from app.models.oauth_connection import OAuthConnection
from app.models.oauth_state import OAuthState
from app.models.user import User
from app.services import oauth_service
from app.services.oauth_service import (
    OAuthConnectorError,
    begin_oauth,
    complete_oauth,
    decrypt_oauth_secret,
    encrypt_oauth_secret,
    provider_config,
    refresh_oauth_connection,
)


def _register_and_login(client, email: str):
    client.post("/auth/register", json={
        "email": email,
        "password": "StrongPass123",
    })
    response = client.post("/auth/login", json={
        "email": email,
        "password": "StrongPass123",
    })
    assert response.status_code == 200
    return client.cookies.get("access_token")


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeAsyncClient:
    responses = []
    calls = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, data=None, headers=None):
        FakeAsyncClient.calls.append(("post", url, data, headers))
        payload = FakeAsyncClient.responses.pop(0)
        return FakeResponse(payload)

    async def get(self, url, headers=None):
        FakeAsyncClient.calls.append(("get", url, headers))
        payload = FakeAsyncClient.responses.pop(0)
        return FakeResponse(payload)


def _configure_google(monkeypatch):
    monkeypatch.setattr(oauth_service.settings, "OAUTH_CALLBACK_BASE_URL", "https://api.example.com")
    monkeypatch.setattr(oauth_service.settings, "OAUTH_GOOGLE_CLIENT_ID", "google-client")
    monkeypatch.setattr(oauth_service.settings, "OAUTH_GOOGLE_CLIENT_SECRET", "google-secret")
    monkeypatch.setattr(oauth_service.settings, "OAUTH_MICROSOFT_CLIENT_ID", "")
    monkeypatch.setattr(oauth_service.settings, "OAUTH_MICROSOFT_CLIENT_SECRET", "")


def test_provider_config_requires_credentials(monkeypatch):
    monkeypatch.setattr(oauth_service.settings, "OAUTH_GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(oauth_service.settings, "OAUTH_GOOGLE_CLIENT_SECRET", "")

    with pytest.raises(OAuthConnectorError, match="not configured"):
        provider_config("google")


def test_begin_oauth_creates_pkce_state_and_authorization_url(db_session, monkeypatch):
    _configure_google(monkeypatch)
    user = User(email="oauth-start@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    url, expires_at = begin_oauth("google", user.id, db_session)

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "accounts.google.com"
    assert params["response_type"] == ["code"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["client_id"] == ["google-client"]
    assert params["redirect_uri"] == ["https://api.example.com/oauth/google/callback"]
    stored_state = db_session.query(OAuthState).first()
    assert stored_state is not None
    assert expires_at == stored_state.expires_at


def test_oauth_secret_is_encrypted_at_rest(monkeypatch):
    monkeypatch.setattr(oauth_service.settings, "JWT_SECRET_KEY", "test-jwt-secret")

    secret = "access-token-value"
    encrypted = encrypt_oauth_secret(secret)

    assert encrypted != secret
    assert decrypt_oauth_secret(encrypted) == secret


def test_complete_oauth_exchanges_code_fetches_identity_and_persists_connection(
    db_session,
    monkeypatch,
):
    _configure_google(monkeypatch)
    user = User(email="oauth-complete@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    user_id = user.id
    authorization_url, _ = begin_oauth("google", user_id, db_session)
    state = parse_qs(urlparse(authorization_url).query)["state"][0]

    FakeAsyncClient.responses = [
        {
            "access_token": "access-1",
            "refresh_token": "refresh-1",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "openid email profile",
        },
        {"sub": "google-user-1", "email": "google@example.com"},
    ]
    FakeAsyncClient.calls = []
    monkeypatch.setattr(oauth_service.httpx, "AsyncClient", FakeAsyncClient)

    connection = asyncio.run(
        complete_oauth(
            "google",
            user_id,
            state,
            "auth-code",
            db_session,
        )
    )

    assert connection.provider == "google"
    assert connection.subject == "google-user-1"
    assert connection.email == "google@example.com"
    assert connection.scopes == ["openid", "email", "profile"]
    assert decrypt_oauth_secret(connection.access_token_encrypted) == "access-1"
    assert decrypt_oauth_secret(connection.refresh_token_encrypted) == "refresh-1"
    assert db_session.query(OAuthState).first().used_at is not None
    assert FakeAsyncClient.calls[0][2]["code_verifier"]
    assert FakeAsyncClient.calls[0][2]["code"] == "auth-code"


def test_oauth_state_cannot_be_replayed(db_session, monkeypatch):
    _configure_google(monkeypatch)
    user = User(email="oauth-replay@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    authorization_url, _ = begin_oauth("google", user.id, db_session)
    state = parse_qs(urlparse(authorization_url).query)["state"][0]

    FakeAsyncClient.responses = [
        {
            "access_token": "access-1",
            "refresh_token": "refresh-1",
            "expires_in": 3600,
        },
        {"sub": "google-user-1"},
    ]
    monkeypatch.setattr(oauth_service.httpx, "AsyncClient", FakeAsyncClient)

    asyncio.run(
        complete_oauth("google", 1, state, "auth-code", db_session)
    )

    with pytest.raises(OAuthConnectorError, match="invalid or expired"):
        asyncio.run(
            complete_oauth("google", 1, state, "auth-code", db_session)
        )


def test_refresh_oauth_connection_rotates_tokens(db_session, monkeypatch):
    _configure_google(monkeypatch)
    owner = User(email="oauth-refresh@example.com", hashed_password="x")
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    connection = OAuthConnection(
        user_id=owner.id,
        provider="google",
        subject="google-user-2",
        email="refresh@example.com",
        access_token_encrypted=encrypt_oauth_secret("old-access"),
        refresh_token_encrypted=encrypt_oauth_secret("old-refresh"),
        token_type="Bearer",
        scopes=["openid"],
    )
    db_session.add(connection)
    db_session.commit()
    db_session.refresh(connection)

    FakeAsyncClient.responses = [
        {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 1800,
            "scope": "openid email",
        }
    ]
    monkeypatch.setattr(oauth_service.httpx, "AsyncClient", FakeAsyncClient)

    refreshed = asyncio.run(
        refresh_oauth_connection(connection, db_session)
    )

    assert decrypt_oauth_secret(refreshed.access_token_encrypted) == "new-access"
    assert decrypt_oauth_secret(refreshed.refresh_token_encrypted) == "new-refresh"
    assert refreshed.scopes == ["openid", "email"]


def test_connection_owner_isolation(client, db_session, monkeypatch):
    _configure_google(monkeypatch)

    owner_token = _register_and_login(client, "oauth-owner@example.com")
    other_token = _register_and_login(client, "oauth-other@example.com")

    db_user = (
        db_session.query(User)
        .filter_by(email="oauth-owner@example.com")
        .first()
    )
    connection = OAuthConnection(
        user_id=db_user.id,
        provider="google",
        subject="isolated-user",
        email="owner@example.com",
        access_token_encrypted=encrypt_oauth_secret("access"),
        refresh_token_encrypted=None,
        token_type="Bearer",
        scopes=["openid"],
    )
    db_session.add(connection)
    db_session.commit()
    db_session.refresh(connection)

    response = client.delete(
        f"/oauth/connections/{connection.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert response.status_code == 404

    listed = client.get(
        "/oauth/connections",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert listed.status_code == 200
    assert listed.json() == []


def test_oauth_providers_endpoint_lists_only_configured(client, monkeypatch):
    token = _register_and_login(client, "oauth-providers@example.com")
    _configure_google(monkeypatch)

    response = client.get(
        "/oauth/providers",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == [{"provider": "google"}]
