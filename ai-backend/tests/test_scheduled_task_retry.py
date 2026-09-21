"""اختبارات إعادة محاولة تنفيذ مهمة مجدولة فاشلة."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _create_workspace(client, token):
    return client.post(
        "/workspaces",
        json={"name": "Retry Tests"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()


def test_retry_failed_run(client, monkeypatch):
    token = _register_and_login(client, "retry-test@example.com")
    workspace = _create_workspace(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace["id"],
            "prompt": "نفذ المهمة",
            "schedule_type": "once",
            "next_run_at": future,
        },
        headers=headers,
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    async def failing_reply(*args, **kwargs):
        raise RuntimeError("فشل تجريبي")

    monkeypatch.setattr(chat_router_module, "get_ai_reply", failing_reply)

    failed = client.post(f"/scheduled-tasks/{task_id}/run", headers=headers)
    assert failed.status_code == 202
    failed_run_id = failed.json()["id"]
    assert failed.json()["status"] == "failed"

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="نجح")),
    )

    retry = client.post(
        f"/scheduled-tasks/{task_id}/runs/{failed_run_id}/retry",
        headers=headers,
    )
    assert retry.status_code == 202
    assert retry.json()["scheduled_task_id"] == task_id
