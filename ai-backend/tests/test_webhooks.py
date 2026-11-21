import hashlib
import hmac

import pytest

from app.models.user import User
from app.models.webhook_delivery import WebhookDelivery
from app import tasks as tasks_module
from app.routers import api_keys as api_keys_router
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
    fake_enqueue = lambda ids: queued.extend(ids)
    monkeypatch.setattr(webhooks_router, "enqueue_webhook_deliveries", fake_enqueue)
    monkeypatch.setattr(api_keys_router, "enqueue_webhook_deliveries", fake_enqueue)

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
            # The sending state must remain uncommitted while HTTP is in flight;
            # this preserves the row lock against the recovery sweep.
            assert delivery.status == "sending"
            assert delivery in db_session.dirty
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


def test_webhook_delivery_outbox_requeues_due_and_recovers_stale_sends(
    db_session, monkeypatch
):
    from datetime import datetime, timedelta, timezone
    from app.models.webhook_endpoint import WebhookEndpoint

    user = User(email="webhook-outbox@example.com", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    endpoint = WebhookEndpoint(
        user_id=user.id,
        name="Outbox",
        url="https://example.test/hook",
        secret_encrypted=encrypt_webhook_secret("whsec_outbox"),
        event_types=["webhook.test"],
        is_active=True,
    )
    db_session.add(endpoint)
    db_session.flush()

    due = WebhookDelivery(
        webhook_endpoint_id=endpoint.id,
        event_id="evt-outbox-due",
        event_type="webhook.test",
        payload={"kind": "due"},
        status="queued",
    )
    stale = WebhookDelivery(
        webhook_endpoint_id=endpoint.id,
        event_id="evt-outbox-stale",
        event_type="webhook.test",
        payload={"kind": "stale"},
        status="sending",
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    future = WebhookDelivery(
        webhook_endpoint_id=endpoint.id,
        event_id="evt-outbox-future",
        event_type="webhook.test",
        payload={"kind": "future"},
        status="queued",
        next_attempt_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db_session.add_all([due, stale, future])
    db_session.commit()

    queued_ids = []

    class FakeTask:
        def delay(self, delivery_id):
            queued_ids.append(delivery_id)

    # The outbox runner owns and closes its Session. Use an independent
    # SAVEPOINT-backed session so it cannot close the fixture's db_session.
    from sqlalchemy.orm import Session

    worker_session = Session(
        bind=db_session.connection(),
        join_transaction_mode="create_savepoint",
    )
    monkeypatch.setattr(tasks_module, "SessionLocal", lambda: worker_session)
    monkeypatch.setattr(tasks_module, "deliver_webhook_task", FakeTask())

    due_id, stale_id = due.id, stale.id
    assert tasks_module._run_webhook_delivery_outbox_batch() == 2
    assert set(queued_ids) == {due_id, stale_id}
    assert set(queued_ids) == {due.id, stale.id}
    db_session.refresh(stale)
    assert stale.status == "queued"
    assert stale.next_attempt_at is not None
    db_session.refresh(future)
    assert future.status == "queued"


def test_webhook_delivery_ignores_duplicate_task_while_sending(db_session, monkeypatch):
    from app.models.webhook_endpoint import WebhookEndpoint

    user = User(email="webhook-duplicate@example.com", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    endpoint = WebhookEndpoint(
        user_id=user.id,
        name="Duplicate",
        url="https://example.test/hook",
        secret_encrypted=encrypt_webhook_secret("whsec_duplicate"),
        event_types=["webhook.test"],
        is_active=True,
    )
    db_session.add(endpoint)
    db_session.flush()
    delivery = WebhookDelivery(
        webhook_endpoint_id=endpoint.id,
        event_id="evt-duplicate",
        event_type="webhook.test",
        payload={"hello": "world"},
        status="sending",
        attempt_count=1,
    )
    db_session.add(delivery)
    db_session.commit()

    def forbidden_http_client(*args, **kwargs):
        raise AssertionError("duplicate delivery must not perform HTTP I/O")

    monkeypatch.setattr(webhook_service.httpx, "Client", forbidden_http_client)
    webhook_service.deliver_webhook_delivery(delivery.id, db=db_session)
    db_session.refresh(delivery)
    assert delivery.status == "sending"
    assert delivery.attempt_count == 1



def test_webhook_network_error_persists_failed_after_max_attempts(
    db_session, monkeypatch
):
    from sqlalchemy.orm import Session
    from app.models.webhook_endpoint import WebhookEndpoint
    from app.services import webhook_service

    user = User(email="webhook-max-attempts@example.com", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    endpoint = WebhookEndpoint(
        user_id=user.id,
        name="Max Attempts",
        url="https://example.test/hook",
        secret_encrypted=encrypt_webhook_secret("whsec_max_attempts"),
        event_types=["webhook.test"],
        is_active=True,
    )
    db_session.add(endpoint)
    db_session.flush()
    delivery = WebhookDelivery(
        webhook_endpoint_id=endpoint.id,
        event_id="evt-max-attempts",
        event_type="webhook.test",
        payload={"kind": "max-attempts"},
        status="queued",
        attempt_count=4,
    )
    db_session.add(delivery)
    db_session.commit()

    monkeypatch.setattr(webhook_service, "validate_webhook_url", lambda url: url)

    class FailingClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise OSError("simulated network outage")

    monkeypatch.setattr(webhook_service.httpx, "Client", FailingClient)

    # Give the delivery function an owned session, then verify state using a
    # separately opened session after the owned one has been closed.
    connection = db_session.connection()
    session_factory = lambda: Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )
    monkeypatch.setattr("app.database.SessionLocal", session_factory)
    webhook_service.deliver_webhook_delivery(delivery.id)

    verification_session = session_factory()
    try:
        persisted = verification_session.get(WebhookDelivery, delivery.id)
        assert persisted.status == "failed"
        assert persisted.attempt_count == 5
        assert persisted.next_attempt_at is None
    finally:
        verification_session.close()

    queued_ids = []

    class FakeTask:
        def delay(self, delivery_id):
            queued_ids.append(delivery_id)

    monkeypatch.setattr(tasks_module, "SessionLocal", session_factory)
    monkeypatch.setattr(tasks_module, "deliver_webhook_task", FakeTask())
    assert tasks_module._run_webhook_delivery_outbox_batch() == 0
    assert queued_ids == []
