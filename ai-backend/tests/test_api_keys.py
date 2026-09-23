"""اختبارات مفاتيح API ونقطة المطورين."""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.models.api_key import APIKey
from app.models.usage_log import UsageLog
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


def test_api_key_rate_limit_headers_report_remaining_and_reset(client, monkeypatch):
    monkeypatch.setattr(
        api_keys_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد API", input_tokens=1, output_tokens=1)),
    )
    token = _register_and_login(client, "developer-rate-headers@example.com")
    session_headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/api-keys",
        json={"name": "Headers", "daily_request_limit": 3},
        headers=session_headers,
    )
    assert created.status_code == 201
    secret = created.json()["secret"]

    first = client.post(
        "/v1/chat",
        json={"message": "الأولى"},
        headers={"X-API-Key": secret},
    )
    assert first.status_code == 200
    assert first.headers["X-RateLimit-Limit"] == "3"
    assert first.headers["X-RateLimit-Remaining"] == "2"
    assert int(first.headers["X-RateLimit-Reset"]) > 0

    second = client.post(
        "/v1/chat",
        json={"message": "الثانية"},
        headers={"X-API-Key": secret},
    )
    assert second.status_code == 200
    assert second.headers["X-RateLimit-Remaining"] == "1"

    third = client.post(
        "/v1/chat",
        json={"message": "الثالثة"},
        headers={"X-API-Key": secret},
    )
    assert third.status_code == 200
    assert third.headers["X-RateLimit-Remaining"] == "0"


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
    assert blocked.headers["X-RateLimit-Limit"] == "1"
    assert blocked.headers["X-RateLimit-Remaining"] == "0"
    assert int(blocked.headers["X-RateLimit-Reset"]) > 0
    assert int(blocked.headers["Retry-After"]) >= 1


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
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            UsageLog(
                user_id=db_key.user_id,
                api_key_id=db_key.id,
                endpoint="/v1/chat",
                input_tokens=10,
                output_tokens=20,
                created_at=now - timedelta(hours=1),
            ),
            UsageLog(
                user_id=db_key.user_id,
                api_key_id=db_key.id,
                endpoint="/v1/chat",
                input_tokens=3,
                output_tokens=7,
                created_at=now - timedelta(days=2),
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
