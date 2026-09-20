"""اختبارات مفاتيح API ونقطة المطورين."""
from unittest.mock import AsyncMock

from app.routers import api_keys as api_keys_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email):
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    response = client.post("/auth/login", json={"email": email, "password": "StrongPass123"})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_create_list_and_revoke_api_key(client):
    token = _register_and_login(client, "api-keys@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/api-keys", json={"name": "CLI"}, headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "CLI"
    assert body["secret"].startswith("ak_live_")
    assert body["key_prefix"] == body["secret"][:16]

    listed = client.get("/api-keys", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == body["id"]
    assert "secret" not in listed.json()[0]
    assert listed.json()[0]["revoked_at"] is None

    revoked = client.delete(f"/api-keys/{body['id']}", headers=headers)
    assert revoked.status_code == 204

    listed_after = client.get("/api-keys", headers=headers)
    assert listed_after.json()[0]["revoked_at"] is not None


def test_api_key_auth_and_chat(client, monkeypatch):
    monkeypatch.setattr(
        api_keys_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد API", input_tokens=2, output_tokens=3)),
    )
    token = _register_and_login(client, "developer-api@example.com")
    session_headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api-keys",
        json={"name": "Integration"},
        headers=session_headers,
    )
    secret = created.json()["secret"]

    response = client.post(
        "/v1/chat",
        json={"message": "مرحبا من API"},
        headers={"X-API-Key": secret},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "رد API"
    assert body["model"]


def test_invalid_and_revoked_api_key_rejected(client):
    token = _register_and_login(client, "developer-reject@example.com")
    session_headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api-keys",
        json={"name": "Integration"},
        headers=session_headers,
    )
    body = created.json()
    secret = body["secret"]

    assert client.post(
        "/v1/chat",
        json={"message": "x"},
        headers={"X-API-Key": "ak_live_invalid"},
    ).status_code == 401

    assert client.delete(
        f"/api-keys/{body['id']}",
        headers=session_headers,
    ).status_code == 204

    assert client.post(
        "/v1/chat",
        json={"message": "x"},
        headers={"X-API-Key": secret},
    ).status_code == 401


def test_cannot_manage_other_users_api_key(client):
    token_a = _register_and_login(client, "api-key-owner@example.com")
    created = client.post(
        "/api-keys",
        json={"name": "Owner key"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    key_id = created.json()["id"]

    token_b = _register_and_login(client, "api-key-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    assert client.delete(f"/api-keys/{key_id}", headers=headers_b).status_code == 404
