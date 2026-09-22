"""
اختبارات المرحلة السابعة: لوحة الإدارة
"""
from unittest.mock import AsyncMock

from app.config import settings as app_settings
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123", admin=False):
    if admin:
        app_settings.INITIAL_ADMIN_EMAIL = email
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_admin_endpoints_reject_regular_user(client, monkeypatch):
    admin_token = _register_and_login(client, "first_admin@example.com", admin=True)
    assert admin_token
    token = _register_and_login(client, "regular@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/admin/stats", headers=headers).status_code == 403
    assert client.get("/admin/users", headers=headers).status_code == 403
    assert client.get("/admin/conversations", headers=headers).status_code == 403
    assert client.get("/admin/logs", headers=headers).status_code == 403


def test_admin_stats_reflects_activity(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    admin_token = _register_and_login(client, "statsadmin@example.com", admin=True)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client.post("/chat", json={"message": "مرحبا"}, headers=admin_headers)

    response = client.get("/admin/stats", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_users"] == 1
    assert body["total_conversations"] == 1
    assert body["total_messages"] == 2
    assert body["total_ai_requests"] == 1


def test_admin_can_list_and_update_users(client):
    admin_token = _register_and_login(client, "adminuser@example.com", admin=True)
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

    login_response = client.post(
        "/auth/login", json={"email": "targetuser@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code in (401, 403)


def test_admin_cannot_delete_own_account_via_admin_route(client):
    admin_token = _register_and_login(client, "selfdelete@example.com", admin=True)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    me = client.get("/users/me", headers=admin_headers).json()

    response = client.delete(f"/admin/users/{me['id']}", headers=admin_headers)
    assert response.status_code == 400


def test_admin_can_delete_other_user(client):
    admin_token = _register_and_login(client, "deleter_admin@example.com", admin=True)
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
    admin_token = _register_and_login(client, "convadmin@example.com", admin=True)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    user_token = _register_and_login(client, "convuser@example.com")
    chat_response = client.post(
        "/chat", json={"message": "محادثة المستخدم"}, headers={"Authorization": f"Bearer {user_token}"}
    )
    conversation_id = chat_response.json()["conversation_id"]

    list_response = client.get("/admin/conversations", headers=admin_headers)
    assert list_response.status_code == 200
    assert any(c["id"] == conversation_id for c in list_response.json())
    matching = next(c for c in list_response.json() if c["id"] == conversation_id)
    assert matching["user_email"] == "convuser@example.com"

    delete_response = client.delete(f"/admin/conversations/{conversation_id}", headers=admin_headers)
    assert delete_response.status_code == 204


def test_admin_logs_capture_key_events(client):
    admin_token = _register_and_login(client, "logsadmin@example.com", admin=True)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.get("/admin/logs", headers=admin_headers)
    assert response.status_code == 200
    event_types = [entry["event_type"] for entry in response.json()]
    assert "register" in event_types
    assert "login" in event_types


def test_daily_analytics_includes_today_with_activity(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    admin_token = _register_and_login(client, "analyticsadmin@example.com", admin=True)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    client.post("/chat", json={"message": "مرحبا"}, headers=admin_headers)

    response = client.get("/admin/analytics/daily?days=7", headers=admin_headers)
    assert response.status_code == 200
    points = response.json()
    assert len(points) == 8
    today = points[-1]
    assert today["new_users"] >= 1
    assert today["ai_requests"] >= 1


def test_daily_analytics_requires_admin(client):
    _register_and_login(client, "first_for_analytics@example.com", admin=True)
    token = _register_and_login(client, "nonadmin_analytics@example.com")
    response = client.get(
        "/admin/analytics/daily", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_export_analytics_csv(client):
    admin_token = _register_and_login(client, "csvadmin@example.com", admin=True)
    response = client.get(
        "/admin/analytics/export.csv", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "date,new_users" in response.text



def test_feedback_analytics_requires_admin_and_counts_ratings(client, monkeypatch, db_session):
    from app.models.conversation import Conversation, Message, MessageRole
    from app.models.user import User, UserRole
    from app.routers import chat as chat_router_module
    from app.services.ai_providers.base import AIReply
    from unittest.mock import AsyncMock

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "feedback-admin@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "سؤال"},
        headers=headers,
    ).json()["conversation_id"]

    conversation = db_session.get(Conversation, conversation_id)
    messages = (
        db_session.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.asc())
        .all()
    )
    messages[1].feedback = 1
    db_session.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content="رد ثاني",
            feedback=-1,
        )
    )
    db_session.commit()

    user_response = client.get("/admin/analytics/feedback", headers=headers)
    assert user_response.status_code == 403

    user = db_session.get(User, conversation.user_id)
    user.role = UserRole.admin
    db_session.commit()

    response = client.get("/admin/analytics/feedback?days=30", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_rated"] == 2
    assert data["positive"] == 1
    assert data["negative"] == 1
    assert data["positive_rate"] == 50.0


def test_model_usage_analytics_groups_requests_by_model(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    monkeypatch.setattr(app_settings, "AI_MODEL", "test-model")
    monkeypatch.setattr(app_settings, "AI_ALLOWED_MODELS", ["test-model"])
    admin_token = _register_and_login(client, "model-analytics-admin@example.com", admin=True)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    response = client.post(
        "/chat",
        json={"message": "مرحبا", "model": "test-model"},
        headers=admin_headers,
    )
    assert response.status_code == 200

    usage_response = client.get(
        "/admin/analytics/models?days=30",
        headers=admin_headers,
    )
    assert usage_response.status_code == 200
    rows = usage_response.json()
    assert rows
    row = next(item for item in rows if item["model"] == "test-model")
    assert row["requests"] >= 1
    assert row["total_tokens"] >= 0


def test_model_usage_analytics_requires_admin(client):
    token = _register_and_login(client, "model-analytics-user@example.com")
    response = client.get(
        "/admin/analytics/models",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_cost_usage_analytics_estimates_configured_pricing(client, db_session, monkeypatch):
    from app.models.usage_log import UsageLog
    import json

    admin_token = _register_and_login(client, "cost-analytics-admin@example.com", admin=True)
    headers = {"Authorization": f"Bearer {admin_token}"}
    user_id = client.get("/users/me", headers=headers).json()["id"]

    monkeypatch.setattr(
        app_settings,
        "AI_PRICING_JSON",
        json.dumps(
            {
                "gemini:gemini-2.5-flash": {
                    "input_per_million_usd": 1.0,
                    "output_per_million_usd": 2.0,
                }
            }
        ),
    )

    db_session.add(
        UsageLog(
            user_id=user_id,
            endpoint="/chat",
            provider="gemini",
            model="gemini-2.5-flash",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )
    )
    db_session.commit()

    response = client.get("/admin/analytics/cost?days=30", headers=headers)
    assert response.status_code == 200
    row = response.json()[0]
    assert row["pricing_configured"] is True
    assert row["input_cost_usd"] == 1.0
    assert row["output_cost_usd"] == 1.0
    assert row["total_cost_usd"] == 2.0


def test_cost_usage_analytics_marks_unknown_pricing(client, db_session, monkeypatch):
    from app.models.usage_log import UsageLog

    admin_token = _register_and_login(client, "cost-unknown-admin@example.com", admin=True)
    headers = {"Authorization": f"Bearer {admin_token}"}
    user_id = client.get("/users/me", headers=headers).json()["id"]

    monkeypatch.setattr(app_settings, "AI_PRICING_JSON", "{}")
    db_session.add(
        UsageLog(
            user_id=user_id,
            endpoint="/chat",
            provider="unknown-provider",
            model="unknown-model",
            input_tokens=100,
            output_tokens=200,
        )
    )
    db_session.commit()

    response = client.get("/admin/analytics/cost?days=30", headers=headers)
    assert response.status_code == 200
    row = response.json()[0]
    assert row["pricing_configured"] is False
    assert row["total_cost_usd"] is None



def test_cost_budget_reports_month_spend_and_remaining(client, db_session, monkeypatch):
    from app.models.usage_log import UsageLog
    import json

    admin_token = _register_and_login(client, "budget-admin@example.com", admin=True)
    headers = {"Authorization": f"Bearer {admin_token}"}
    user_id = client.get("/users/me", headers=headers).json()["id"]

    monkeypatch.setattr(app_settings, "AI_MONTHLY_BUDGET_USD", 5.0)
    monkeypatch.setattr(
        app_settings,
        "AI_PRICING_JSON",
        json.dumps(
            {
                "gemini:gemini-2.5-flash": {
                    "input_per_million_usd": 1.0,
                    "output_per_million_usd": 2.0,
                }
            }
        ),
    )
    db_session.add(
        UsageLog(
            user_id=user_id,
            endpoint="/chat",
            provider="gemini",
            model="gemini-2.5-flash",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )
    )
    db_session.commit()

    response = client.get("/admin/analytics/budget", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["budget_usd"] == 5.0
    assert data["spent_usd"] == 2.0
    assert data["remaining_usd"] == 3.0
    assert data["usage_percent"] == 40.0
    assert data["over_budget"] is False
    assert data["pricing_configured"] is True


def test_cost_budget_marks_unpriced_usage_without_guessing_cost(client, db_session, monkeypatch):
    from app.models.usage_log import UsageLog

    admin_token = _register_and_login(client, "budget-unpriced-admin@example.com", admin=True)
    headers = {"Authorization": f"Bearer {admin_token}"}
    user_id = client.get("/users/me", headers=headers).json()["id"]

    monkeypatch.setattr(app_settings, "AI_MONTHLY_BUDGET_USD", 5.0)
    monkeypatch.setattr(app_settings, "AI_PRICING_JSON", "{}")
    db_session.add(
        UsageLog(
            user_id=user_id,
            endpoint="/chat",
            provider="unknown-provider",
            model="unknown-model",
            input_tokens=100,
            output_tokens=200,
        )
    )
    db_session.commit()

    response = client.get("/admin/analytics/budget", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["spent_usd"] == 0.0
    assert data["unpriced_requests"] == 1
    assert data["pricing_configured"] is False
    assert data["over_budget"] is False


def test_cost_budget_requires_admin(client):
    token = _register_and_login(client, "budget-user@example.com")
    response = client.get(
        "/admin/analytics/budget",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_can_list_and_update_plan_entitlements(client, db_session):
    from app.models.plan import Plan

    admin_token = _register_and_login(client, "plan-admin@example.com")
    admin = client.get("/users/me", headers={"Authorization": f"Bearer {admin_token}"}).json()
    user = db_session.get(User, admin["id"])
    user.role = UserRole.admin
    db_session.commit()

    plans = client.get("/admin/plans", headers={"Authorization": f"Bearer {admin_token}"})
    assert plans.status_code == 200
    assert plans.json()

    plan = plans.json()[0]
    response = client.patch(
        f"/admin/plans/{plan['id']}",
        json={
            "daily_ai_request_limit": 42,
            "allowed_models": ["gemini-2.5-flash", "*", "gemini-2.5-flash"],
            "is_active": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["daily_ai_request_limit"] == 42
    assert response.json()["allowed_models"] == ["gemini-2.5-flash", "*"]
    assert response.json()["is_active"] is False


def test_non_admin_cannot_manage_plans(client):
    token = _register_and_login(client, "plan-user@example.com")
    assert client.get(
        "/admin/plans",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 403
