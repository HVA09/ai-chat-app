import hashlib
import hmac

import pytest

from app.models.user import User
from app.models.webhook_delivery import WebhookDelivery
from app.routers import webhooks as webhooks_router
from app.services import webhook_service
from app.services.webhook_service import (
    WebhookValidationError,
    decrypt_webhook_secret,
    encrypt_webhook_secret,
    generate_webhook_secret,
    sign_webhook,
    validate_webhook_url,
)


def _register_and_login(client, email: str):
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_webhook_secret_is_returned_only_at_creation(client, monkeypatch):
    monkeypatch.setattr(webhooks_router, "validate_webhook_url", lambda url: url)

    token = _register_and_login(client, "webhook-create@example.com")
    response = client.post(
        "/webhooks",
        json={
            "name": "My Webhook",
            "url": "https://example.test/hook",
            "event_types": ["api_key.created"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["secret"].startswith("whsec_")
    endpoint_id = data["id"]

    listed = client.get(
        "/webhooks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listed.status_code == 200
    assert "secret" not in listed.json()[0]

    rotated = client.patch(
        f"/webhooks/{endpoint_id}",
        json={"rotate_secret": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rotated.status_code == 200
    assert rotated.json()["secret"] != data["secret"]


def test_webhook_owner_isolation(client, monkeypatch):
    monkeypatch.setattr(webhooks_router, "validate_webhook_url", lambda url: url)

    owner_token = _register_and_login(client, "webhook-owner@example.com")
    other_token = _register_and_login(client, "webhook-other@example.com")

    response = client.post(
        "/webhooks",
        json={
            "name": "Private",
            "url": "https://example.test/hook",
            "event_types": ["webhook.test"],
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    endpoint_id = response.json()["id"]

    assert client.get(
        "/webhooks",
        headers={"Authorization": f"Bearer {other_token}"},
    ).json() == []

    assert client.delete(
        f"/webhooks/{endpoint_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    ).status_code == 404


def test_webhook_test_queues_delivery(client, monkeypatch, db_session):
    monkeypatch.setattr(webhooks_router, "validate_webhook_url", lambda url: url)
    queued = []
    monkeypatch.setattr(
        webhooks_router,
        "enqueue_webhook_deliveries",
        lambda delivery_ids: queued.extend(delivery_ids),
    )

    token = _register_and_login(client, "webhook-test@example.com")
    created = client.post(
        "/webhooks",
        json={
            "name": "Tester",
            "url": "https://example.test/hook",
            "event_types": ["webhook.test"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    endpoint_id = created.json()["id"]

    response = client.post(
        f"/webhooks/{endpoint_id}/test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 202
    assert len(response.json()) == 1
    assert queued == [response.json()[0]["id"]]

    delivery = db_session.get(WebhookDelivery, response.json()[0]["id"])
    assert delivery.event_type == "webhook.test"


def test_sign_webhook_uses_hmac_sha256():
    secret = "whsec_demo"
    body = b'{"hello":"world"}'
    timestamp = 1700000000

    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.".encode() + body,
        hashlib.sha256,
    ).hexdigest()

    assert sign_webhook(secret, timestamp, body) == f"sha256={expected}"


def test_webhook_secret_round_trip():
    secret = generate_webhook_secret()
    encrypted = encrypt_webhook_secret(secret)
    assert encrypted != secret
    assert decrypt_webhook_secret(encrypted) == secret


def test_webhook_url_rejects_private_addresses(monkeypatch):
    with pytest.raises(WebhookValidationError):
        validate_webhook_url("http://127.0.0.1:8000/hook")

    monkeypatch.setattr(
        webhook_service.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(2, 1, 6, "", ("10.0.0.5", 0))],
    )
    with pytest.raises(WebhookValidationError):
        validate_webhook_url("http://example.test/hook")


def test_api_key_creation_emits_webhook_event(client, monkeypatch, db_session):
    monkeypatch.setattr(webhooks_router, "validate_webhook_url", lambda url: url)
    queued = []
    monkeypatch.setattr(
        webhooks_router,
        "enqueue_webhook_deliveries",
        lambda ids: queued.extend(ids),
    )

    token = _register_and_login(client, "webhook-api-key@example.com")
    client.post(
        "/webhooks",
        json={
            "name": "API Key Listener",
            "url": "https://example.test/hook",
            "event_types": ["api_key.created"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    created = client.post(
        "/api-keys",
        json={"name": "event-key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201

    delivery = (
        db_session.query(WebhookDelivery)
        .order_by(WebhookDelivery.id.desc())
        .first()
    )
    assert delivery is not None
    assert delivery.event_type == "api_key.created"
    assert delivery.payload["name"] == "event-key"
    assert queued


def test_delivery_sends_signed_request_and_marks_delivered(db_session, monkeypatch):
    from app.models.webhook_endpoint import WebhookEndpoint
    from app.services.webhook_service import deliver_webhook_delivery

    user = User(email="webhook-delivery@example.com", hashed_password="x")
    db_session.add(user)
    db_session.flush()

    endpoint = WebhookEndpoint(
        user_id=user.id,
        name="Delivery",
        url="https://example.test/hook",
        secret_encrypted=encrypt_webhook_secret("whsec_delivery"),
        event_types=["webhook.test"],
        is_active=True,
    )
    db_session.add(endpoint)
    db_session.flush()
    delivery = WebhookDelivery(
        webhook_endpoint_id=endpoint.id,
        event_id="evt_delivery",
        event_type="webhook.test",
        payload={"hello": "world"},
        status="queued",
    )
    db_session.add(delivery)
    db_session.commit()

    monkeypatch.setattr(webhook_service, "validate_webhook_url", lambda url: url)

    sent = {}

    class FakeResponse:
        status_code = 200

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, content, headers):
            sent["url"] = url
            sent["content"] = content
            sent["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(webhook_service.httpx, "Client", FakeClient)

    deliver_webhook_delivery(delivery.id, db=db_session)

    db_session.refresh(delivery)
    assert delivery.status == "delivered"
    assert delivery.response_status == 200
    assert sent["headers"]["X-Webhook-Id"] == "evt_delivery"
    assert sent["headers"]["X-Webhook-Signature"].startswith("sha256=")
