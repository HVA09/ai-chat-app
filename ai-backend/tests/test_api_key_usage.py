"""اختبارات تحليلات استخدام مفاتيح API."""
from datetime import datetime, timedelta, timezone

from app.models.api_key import APIKey
from app.models.usage_log import UsageLog


def _register_and_login(client, email):
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    response = client.post("/auth/login", json={"email": email, "password": "StrongPass123"})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_api_key_usage_endpoint_is_owner_scoped(client, db_session):
    token_a = _register_and_login(client, "usage-key-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    created = client.post("/api-keys", json={"name": "Reports"}, headers=headers_a)
    assert created.status_code == 201
    key = created.json()

    db_key = db_session.get(APIKey, key["id"])
    db_session.add_all([
        UsageLog(
            user_id=db_key.user_id,
            api_key_id=db_key.id,
            endpoint="/v1/chat",
            input_tokens=10,
            output_tokens=20,
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        ),
        UsageLog(
            user_id=db_key.user_id,
            api_key_id=db_key.id,
            endpoint="/v1/chat",
            input_tokens=3,
            output_tokens=7,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        ),
    ])
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
