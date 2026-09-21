"""اختبارات تحليلات استخدام مزوّدي الذكاء الاصطناعي."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.models.usage_log import UsageLog
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_admin_provider_usage_analytics(client, db_session):
    token = _register_and_login(client, "provider-admin@example.com")
    user_id_response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    user_id = user_id_response.json()["id"]

    db_session.add_all(
        [
            UsageLog(
                user_id=user_id,
                endpoint="/chat",
                provider="gemini",
                model="gemini-2.5-flash",
                input_tokens=10,
                output_tokens=5,
                created_at=datetime.now(timezone.utc) - timedelta(days=2),
            ),
            UsageLog(
                user_id=user_id,
                endpoint="/chat",
                provider="openai",
                model="gpt-4o-mini",
                input_tokens=3,
                output_tokens=2,
                created_at=datetime.now(timezone.utc) - timedelta(days=2),
            ),
            UsageLog(
                user_id=user_id,
                endpoint="/chat",
                provider="gemini",
                model="gemini-2.5-flash",
                input_tokens=4,
                output_tokens=6,
                created_at=datetime.now(timezone.utc) - timedelta(days=1),
            ),
        ]
    )
    db_session.commit()

    # upgrade the same account to admin through the test database.
    from app.models.user import User, UserRole

    user = db_session.get(User, user_id)
    user.role = UserRole.admin
    db_session.commit()

    response = client.get(
        "/admin/analytics/providers",
        params={"days": 30},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert {row["provider"] for row in data} == {"gemini", "openai"}
    gemini = next(row for row in data if row["provider"] == "gemini")
    assert gemini["requests"] == 2
    assert gemini["input_tokens"] == 14
    assert gemini["output_tokens"] == 11
    assert gemini["total_tokens"] == 25


def test_ai_reply_records_primary_provider(monkeypatch):
    from app.services import ai_service

    fake = AsyncMock(return_value=AIReply(text="ok"))
    monkeypatch.setattr(ai_service, "get_provider", lambda *args, **kwargs: type(
        "FakeProvider",
        (),
        {"get_reply": fake},
    )())

    async def run():
        return await ai_service.get_ai_reply("hello")

    import asyncio

    reply = asyncio.run(run())
    assert reply.provider == ai_service.settings.AI_PROVIDER


def test_ai_reply_records_fallback_provider(monkeypatch):
    from app.services import ai_service

    primary = type("Primary", (), {})()
    fallback = type("Fallback", (), {})()
    primary.get_reply = AsyncMock(side_effect=RuntimeError("boom"))
    fallback.get_reply = AsyncMock(return_value=AIReply(text="fallback"))

    calls = iter([primary, fallback])

    monkeypatch.setattr(ai_service, "get_provider", lambda *args, **kwargs: next(calls))
    monkeypatch.setattr(ai_service, "_is_retryable_provider_error", lambda exc: True)

    monkeypatch.setattr(ai_service.settings, "AI_FALLBACK_PROVIDER", "deepseek")
    monkeypatch.setattr(ai_service.settings, "AI_FALLBACK_API_KEY", "fallback-key")
    monkeypatch.setattr(ai_service.settings, "AI_FALLBACK_MODEL", "fallback-model")
    monkeypatch.setattr(ai_service.settings, "AI_FALLBACK_API_BASE_URL", "https://example.com")

    import asyncio

    reply = asyncio.run(ai_service.get_ai_reply("hello"))
    assert reply.provider == "deepseek"
