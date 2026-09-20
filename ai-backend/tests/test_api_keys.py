"""اختبارات مفاتيح API ونقطة المطورين."""
from datetime import date, timedelta
from unittest.mock import AsyncMock

from app.models.api_key import APIKey

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
    assert body["daily_request_limit"] is None
    assert body["expires_at"] is None

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


def test_api_key_daily_limit_blocks_second_request(client, monkeypatch):
    monkeypatch.setattr(
        api_keys_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد API", input_tokens=1, output_tokens=1)),
    )
    token = _register_and_login(client, "developer-quota@example.com")
    session_headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api-keys",
        json={"name": "Quota key", "daily_request_limit": 1},
        headers=session_headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["daily_request_limit"] == 1

    secret = body["secret"]
    response = client.post(
        "/v1/chat",
        json={"message": "الأولى"},
        headers={"X-API-Key": secret},
    )
    assert response.status_code == 200

    blocked = client.post(
        "/v1/chat",
        json={"message": "الثانية"},
        headers={"X-API-Key": secret},
    )
    assert blocked.status_code == 429


def test_expired_api_key_is_rejected(client, db_session):
    token = _register_and_login(client, "developer-expiry@example.com")
    session_headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api-keys",
        json={
            "name": "Expired key",
            "expires_at": date.today().isoformat(),
        },
        headers=session_headers,
    )
    assert created.status_code == 201
    body = created.json()

    key = db_session.get(APIKey, body["id"])
    key.expires_at = date.today() - timedelta(days=1)
    db_session.flush()

    response = client.post(
        "/v1/chat",
        json={"message": "انتهى"},
        headers={"X-API-Key": body["secret"]},
    )
    assert response.status_code == 401
    assert "انتهت صلاحية" in response.json()["detail"]


def test_api_key_expiry_in_past_rejected_on_creation(client):
    token = _register_and_login(client, "developer-expiry-validation@example.com")
    response = client.post(
        "/api-keys",
        json={
            "name": "Past key",
            "expires_at": (date.today() - timedelta(days=1)).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_api_key_usage_endpoint_is_owner_scoped(client, db_session):
    token_a = _register_and_login(client, "usage-key-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    created = client.post("/api-keys", json={"name": "Reports"}, headers=headers_a)
    assert created.status_code == 201
    key = created.json()

    db_key = db_session.get(APIKey, key["id"])
    db_session.add_all(
        [
            __import__("app.models.usage_log", fromlist=["UsageLog"]).UsageLog(
                user_id=db_key.user_id,
                api_key_id=db_key.id,
                endpoint="/v1/chat",
                input_tokens=10,
                output_tokens=20,
                created_at=__import__("datetime", fromlist=["datetime"]).datetime.now(
                    __import__("datetime", fromlist=["timezone"]).timezone.utc
                ) - __import__("datetime", fromlist=["timedelta"]).timedelta(hours=1),
            ),
            __import__("app.models.usage_log", fromlist=["UsageLog"]).UsageLog(
                user_id=db_key.user_id,
                api_key_id=db_key.id,
                endpoint="/v1/chat",
                input_tokens=3,
                output_tokens=7,
                created_at=__import__("datetime", fromlist=["datetime"]).datetime.now(
                    __import__("datetime", fromlist=["timezone"]).timezone.utc
                ) - __import__("datetime", fromlist=["timedelta"]).timedelta(days=2),
            ),
        ]
    )
    db_session.flush()

    usage = client.get(f"/api-keys/{key['id']}/usage", headers=headers_a)
    assert usage.status_code == 200
    body = usage.json()
    assert body["used_requests"] == 1
    assert body["input_tokens"] == 10
    assert body["output_tokens"] == 20
    assert body["total_tokens"] == 30
    assert body["window_hours"] == 24

    token_b = _register_and_login(client, "usage-key-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    assert client.get(f"/api-keys/{key['id']}/usage", headers=headers_b).status_code == 404
