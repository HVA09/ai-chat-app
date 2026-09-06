"""
اختبارات مسار المحادثة — يتم عمل mock لاستدعاء محرك AI بدل الاتصال الحقيقي بالإنترنت
"""
from unittest.mock import AsyncMock

from app.config import settings as app_settings
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email="chat@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    return login_response.json()["access_token"]


def test_chat_creates_conversation_and_returns_reply(client, monkeypatch):
    mock_reply = AsyncMock(return_value=AIReply(text="رد تجريبي من المساعد"))
    monkeypatch.setattr(chat_router_module, "get_ai_reply", mock_reply)

    token = _register_and_login(client)
    response = client.post(
        "/chat",
        json={"message": "مرحبًا"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "رد تجريبي من المساعد"
    assert "conversation_id" in body


def test_chat_requires_authentication(client):
    response = client.post("/chat", json={"message": "مرحبًا"})
    assert response.status_code == 401


def test_chat_stores_token_usage(client, monkeypatch, db_session):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد", input_tokens=12, output_tokens=34)),
    )
    token = _register_and_login(client, "tokens@example.com")
    client.post(
        "/chat", json={"message": "مرحبا"}, headers={"Authorization": f"Bearer {token}"}
    )

    from app.models.usage_log import UsageLog

    log = db_session.query(UsageLog).order_by(UsageLog.id.desc()).first()
    assert log.input_tokens == 12
    assert log.output_tokens == 34


def test_chat_rejects_blank_message(client):
    token = _register_and_login(client)
    response = client.post(
        "/chat", json={"message": "   "}, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422


def test_admin_bypasses_daily_limit(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    monkeypatch.setattr(app_settings, "DAILY_AI_REQUEST_LIMIT", 1)

    # أول مستخدم يسجّل بالاختبار يصير admin تلقائيًا
    token = _register_and_login(client, "admin_by_default@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    for _ in range(3):
        response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
        assert response.status_code == 200


def test_regular_user_hits_daily_limit(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    monkeypatch.setattr(app_settings, "DAILY_AI_REQUEST_LIMIT", 1)

    # نسجل مستخدم أول (يصير admin) عشان الثاني يفضل عادي ونختبر الحد عليه
    _register_and_login(client, "admin_placeholder@example.com")
    token = _register_and_login(client, "regular@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/chat", json={"message": "أول رسالة"}, headers=headers)
    assert first.status_code == 200

    second = client.post("/chat", json={"message": "رسالة ثانية"}, headers=headers)
    assert second.status_code == 429
