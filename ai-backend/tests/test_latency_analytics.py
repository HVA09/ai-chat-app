"""اختبارات تحليلات زمن استجابة مزوّدي الذكاء الاصطناعي."""
import asyncio
from unittest.mock import AsyncMock

from app.models.usage_log import UsageLog
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_ai_reply_records_latency(monkeypatch):
    from app.services import ai_service

    async def fake_get_reply(self, message, history):
        await asyncio.sleep(0.005)
        return AIReply(text="ok")

    fake_provider = type("FakeProvider", (), {"get_reply": fake_get_reply})()
    monkeypatch.setattr(ai_service, "get_provider", lambda *args, **kwargs: fake_provider)

    reply = asyncio.run(ai_service.get_ai_reply("hello"))
    assert reply.provider == ai_service.settings.AI_PROVIDER
    assert reply.latency_ms is not None
    assert reply.latency_ms >= 1


def test_admin_latency_analytics(client, db_session):
    token = _register_and_login(client, "latency-admin@example.com")
    user_id = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]

    db_session.add_all(
        [
            UsageLog(
                user_id=user_id,
                endpoint="/chat",
                provider="gemini",
                model="gemini-2.5-flash",
                latency_ms=120,
            ),
            UsageLog(
                user_id=user_id,
                endpoint="/chat",
                provider="gemini",
                model="gemini-2.5-flash",
                latency_ms=180,
            ),
            UsageLog(
                user_id=user_id,
                endpoint="/chat",
                provider="openai",
                model="gpt-4o-mini",
                latency_ms=80,
            ),
        ]
    )
    db_session.commit()

    from app.models.user import User, UserRole

    user = db_session.get(User, user_id)
    user.role = UserRole.admin
    db_session.commit()

    response = client.get(
        "/admin/analytics/latency",
        params={"days": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    rows = response.json()
    assert {row["provider"] for row in rows} == {"gemini", "openai"}

    gemini = next(row for row in rows if row["provider"] == "gemini")
    assert gemini["requests"] == 2
    assert gemini["avg_latency_ms"] == 150
    assert gemini["min_latency_ms"] == 120
    assert gemini["max_latency_ms"] == 180
