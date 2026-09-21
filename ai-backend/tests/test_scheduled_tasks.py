"""اختبارات المهام المجدولة."""
from datetime import datetime, timedelta, timezone

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply
from unittest.mock import AsyncMock


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _create_workspace(client, token, name="Automation"):
    return client.post(
        "/workspaces",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    ).json()


def test_scheduled_task_crud_and_validation(client):
    token = _register_and_login(client, "schedule@example.com")
    workspace = _create_workspace(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    created = client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace["id"],
            "prompt": "لخص أخبار التقنية",
            "schedule_type": "daily",
            "next_run_at": future,
        },
        headers=headers,
    )
    assert created.status_code == 201
    task = created.json()
    assert task["is_active"] is True

    listed = client.get(
        "/scheduled-tasks",
        params={"workspace_id": workspace["id"]},
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == task["id"]

    updated = client.patch(
        f"/scheduled-tasks/{task['id']}",
        json={"is_active": False},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    deleted = client.delete(f"/scheduled-tasks/{task['id']}", headers=headers)
    assert deleted.status_code == 204


def test_scheduled_task_requires_future_time(client):
    token = _register_and_login(client, "schedule-past@example.com")
    workspace = _create_workspace(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    response = client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace["id"],
            "prompt": "مهمة",
            "schedule_type": "once",
            "next_run_at": past,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_cannot_create_task_for_other_workspace(client):
    token_a = _register_and_login(client, "schedule-owner@example.com")
    workspace = _create_workspace(client, token_a, "Private")
    token_b = _register_and_login(client, "schedule-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    response = client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace["id"],
            "prompt": "ممنوع",
            "schedule_type": "once",
            "next_run_at": future,
        },
        headers=headers_b,
    )
    assert response.status_code == 404
