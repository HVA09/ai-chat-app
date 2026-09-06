"""
اختبارات المرحلة السابعة: لوحة الإدارة
"""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.json()["access_token"]


def test_admin_endpoints_reject_regular_user(client):
    # أول مستخدم = admin، فنسجل واحد ثاني عادي
    _register_and_login(client, "first_admin@example.com")
    token = _register_and_login(client, "regular@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/admin/stats", headers=headers).status_code == 403
    assert client.get("/admin/users", headers=headers).status_code == 403
    assert client.get("/admin/conversations", headers=headers).status_code == 403
    assert client.get("/admin/logs", headers=headers).status_code == 403


def test_admin_stats_reflects_activity(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    admin_token = _register_and_login(client, "statsadmin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client.post("/chat", json={"message": "مرحبا"}, headers=admin_headers)

    response = client.get("/admin/stats", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] == 1
    assert body["total_conversations"] == 1
    assert body["total_messages"] == 2  # رسالة المستخدم + رد المساعد
    assert body["total_ai_requests"] == 1


def test_admin_can_list_and_update_users(client):
    admin_token = _register_and_login(client, "adminuser@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    _register_and_login(client, "targetuser@example.com")

    list_response = client.get("/admin/users", headers=admin_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 2

    target = next(u for u in list_response.json() if u["email"] == "targetuser@example.com")

    update_response = client.patch(
        f"/admin/users/{target['id']}", json={"is_active": False}, headers=admin_headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["is_active"] is False

    # المستخدم المعطّل ما يقدر يسجّل دخول بعدها
    login_response = client.post(
        "/auth/login", json={"email": "targetuser@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code in (401, 403)


def test_admin_cannot_delete_own_account_via_admin_route(client):
    admin_token = _register_and_login(client, "selfdelete@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    me = client.get("/users/me", headers=admin_headers).json()

    response = client.delete(f"/admin/users/{me['id']}", headers=admin_headers)
    assert response.status_code == 400


def test_admin_can_delete_other_user(client):
    admin_token = _register_and_login(client, "deleter_admin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    _register_and_login(client, "to_delete@example.com")

    users = client.get("/admin/users", headers=admin_headers).json()
    target = next(u for u in users if u["email"] == "to_delete@example.com")

    response = client.delete(f"/admin/users/{target['id']}", headers=admin_headers)
    assert response.status_code == 204

    login_response = client.post(
        "/auth/login", json={"email": "to_delete@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code in (401, 403)


def test_admin_can_list_and_delete_any_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    admin_token = _register_and_login(client, "convadmin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_token = _register_and_login(client, "convuser@example.com")
    chat_response = client.post(
        "/chat",
        json={"message": "محادثة المستخدم"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    conversation_id = chat_response.json()["conversation_id"]

    list_response = client.get("/admin/conversations", headers=admin_headers)
    assert list_response.status_code == 200
    assert any(c["id"] == conversation_id for c in list_response.json())
    matching = next(c for c in list_response.json() if c["id"] == conversation_id)
    assert matching["user_email"] == "convuser@example.com"

    delete_response = client.delete(
        f"/admin/conversations/{conversation_id}", headers=admin_headers
    )
    assert delete_response.status_code == 204


def test_admin_logs_capture_key_events(client):
    admin_token = _register_and_login(client, "logsadmin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.get("/admin/logs", headers=admin_headers)
    assert response.status_code == 200
    event_types = [entry["event_type"] for entry in response.json()]
    assert "register" in event_types
    assert "login" in event_types


def test_daily_analytics_includes_today_with_activity(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    admin_token = _register_and_login(client, "analyticsadmin@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    client.post("/chat", json={"message": "مرحبا"}, headers=admin_headers)

    response = client.get("/admin/analytics/daily?days=7", headers=admin_headers)
    assert response.status_code == 200
    points = response.json()
    assert len(points) == 8  # اليوم + 7 أيام قبله

    today = points[-1]
    assert today["new_users"] >= 1
    assert today["ai_requests"] >= 1


def test_daily_analytics_requires_admin(client):
    _register_and_login(client, "first_for_analytics@example.com")  # يصير admin
    token = _register_and_login(client, "nonadmin_analytics@example.com")  # عادي
    response = client.get(
        "/admin/analytics/daily", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_export_analytics_csv(client):
    admin_token = _register_and_login(client, "csvadmin@example.com")
    response = client.get(
        "/admin/analytics/export.csv", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "date,new_users" in response.text
