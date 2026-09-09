"""
اختبارات المرحلة العاشرة: الإشعارات (REST + WebSocket الفوري)
"""
from unittest.mock import MagicMock

from app.routers import billing as billing_router_module
from app.services.payment_providers.base import WebhookEvent


def _register_and_login(client, email="notify@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_welcome_notification_created_on_register(client):
    token = _register_and_login(client, "welcome@example.com")
    response = client.get("/notifications", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "welcome" in [n["notification_type"] for n in response.json()]


def test_mark_notification_read(client):
    token = _register_and_login(client, "readtest@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    target = client.get("/notifications", headers=headers).json()[0]
    assert target["is_read"] is False
    response = client.post(f"/notifications/{target['id']}/read", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_read"] is True


def test_mark_all_read(client):
    token = _register_and_login(client, "readall@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/notifications/read-all", headers=headers)
    assert all(n["is_read"] for n in client.get("/notifications", headers=headers).json())


def test_cannot_read_other_users_notification(client):
    token_a = _register_and_login(client, "notifyowner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    target = client.get("/notifications", headers=headers_a).json()[0]
    token_b = _register_and_login(client, "notifyintruder@example.com")
    response = client.post(f"/notifications/{target['id']}/read", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404


def test_notifications_require_authentication(client):
    assert client.get("/notifications").status_code == 401


def test_websocket_rejects_invalid_token(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/notifications") as websocket:
            websocket.receive_json()


def test_websocket_receives_realtime_notification_on_subscription_activated(client, monkeypatch):
    token = _register_and_login(client, "wsuser@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/users/me", headers=headers).json()
    pro_plan = next(p for p in client.get("/billing/plans").json() if p["name"] == "Pro")

    with client.websocket_connect("/ws/notifications") as websocket:
        mock_provider = MagicMock()
        mock_provider.verify_webhook = MagicMock(return_value=WebhookEvent(
            event_type="checkout_completed",
            provider_subscription_id="sub_ws",
            provider_customer_id="cus_ws",
            status="active",
            client_reference_id=str(me["id"]),
            plan_id=str(pro_plan["id"]),
        ))
        monkeypatch.setattr(billing_router_module, "get_payment_provider", lambda: mock_provider)
        client.post("/billing/webhook/stripe", json={"type": "fake"})
        data = websocket.receive_json()
        assert data["title"] == "تم تفعيل اشتراكك"
        assert data["notification_type"] == "billing"
