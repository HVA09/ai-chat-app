"""
اختبارات المرحلة الثامنة: الاشتراكات والدفع (مزوّد الدفع مموّه دائمًا — بدون اتصال حقيقي)
"""
from unittest.mock import AsyncMock, MagicMock

from app.routers import billing as billing_router_module
from app.services.payment_providers.base import CheckoutResult, WebhookEvent


def _register_and_login(client, email="billing@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.json()["access_token"]


def test_list_plans_is_public_and_seeded(client):
    response = client.get("/billing/plans")
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Free" in names
    assert "Pro" in names


def test_get_subscription_returns_null_when_none(client):
    token = _register_and_login(client)
    response = client.get("/billing/subscription", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() is None


def test_checkout_returns_url_from_provider(client, monkeypatch):
    mock_provider = MagicMock()
    mock_provider.create_checkout_session = AsyncMock(
        return_value=CheckoutResult(checkout_url="https://checkout.example.com/session123")
    )
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: mock_provider)

    token = _register_and_login(client)
    plans = client.get("/billing/plans").json()
    pro_plan = next(p for p in plans if p["name"] == "Pro")

    response = client.post(
        "/billing/checkout",
        json={
            "plan_id": pro_plan["id"],
            "success_url": "https://app.example.com/success",
            "cancel_url": "https://app.example.com/cancel",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["checkout_url"] == "https://checkout.example.com/session123"


def test_checkout_rejects_unknown_plan(client, monkeypatch):
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: MagicMock())
    token = _register_and_login(client)

    response = client.post(
        "/billing/checkout",
        json={"plan_id": 999999, "success_url": "https://a.com", "cancel_url": "https://a.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_webhook_checkout_completed_creates_active_subscription(client, monkeypatch):
    token = _register_and_login(client, "webhookuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/users/me", headers=headers).json()
    plans = client.get("/billing/plans").json()
    pro_plan = next(p for p in plans if p["name"] == "Pro")

    mock_provider = MagicMock()
    mock_provider.verify_webhook = MagicMock(
        return_value=WebhookEvent(
            event_type="checkout_completed",
            provider_subscription_id="sub_123",
            provider_customer_id="cus_123",
            status="active",
            client_reference_id=str(me["id"]),
            plan_id=str(pro_plan["id"]),
        )
    )
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: mock_provider)

    response = client.post("/billing/webhook/stripe", json={"type": "fake"})
    assert response.status_code == 200

    sub_response = client.get("/billing/subscription", headers=headers)
    assert sub_response.json()["status"] == "active"
    assert sub_response.json()["plan"]["name"] == "Pro"


def test_webhook_rejects_invalid_signature(client, monkeypatch):
    mock_provider = MagicMock()
    mock_provider.verify_webhook = MagicMock(side_effect=ValueError("bad signature"))
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: mock_provider)

    response = client.post("/billing/webhook/stripe", json={"type": "fake"})
    assert response.status_code == 400


def test_cancel_subscription(client, monkeypatch):
    token = _register_and_login(client, "canceluser@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/users/me", headers=headers).json()
    plans = client.get("/billing/plans").json()
    pro_plan = next(p for p in plans if p["name"] == "Pro")

    mock_provider = MagicMock()
    mock_provider.verify_webhook = MagicMock(
        return_value=WebhookEvent(
            event_type="checkout_completed",
            provider_subscription_id="sub_789",
            provider_customer_id="cus_789",
            status="active",
            client_reference_id=str(me["id"]),
            plan_id=str(pro_plan["id"]),
        )
    )
    monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: mock_provider)
    client.post("/billing/webhook/stripe", json={"type": "fake"})

    mock_provider.cancel_subscription = AsyncMock(return_value=None)
    response = client.post("/billing/cancel", headers=headers)
    assert response.status_code == 200

    sub_response = client.get("/billing/subscription", headers=headers)
    assert sub_response.json()["status"] == "canceled"


def test_billing_requires_authentication(client):
    assert client.get("/billing/subscription").status_code == 401
    assert client.post("/billing/cancel").status_code == 401


def test_checkout_rejects_non_http_urls(client):
    token = _register_and_login(client, "badurl@example.com")
    plans = client.get("/billing/plans").json()
    pro = next(p for p in plans if p["name"] == "Pro")
    response = client.post(
        "/billing/checkout",
        json={
            "plan_id": pro["id"],
            "success_url": "javascript:alert(1)",
            "cancel_url": "https://app.example.com/cancel",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
