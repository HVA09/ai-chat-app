"""اختبارات سجل تنفيذ المهام المجدولة والتشغيل اليدوي."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.models.agent_job import AgentJob
from app.models.scheduled_task import ScheduledTask
from app.models.scheduled_task_run import ScheduledTaskRun, ScheduledTaskRunStatus
from app.services.ai_providers.base import AIReply
from app import tasks as tasks_module


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


def _create_task(client, headers, workspace_id):
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    return client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace_id,
            "prompt": "نفذ تقريرًا مختصرًا",
            "schedule_type": "once",
            "next_run_at": future,
        },
        headers=headers,
    ).json()


def test_manual_run_creates_history_and_conversation(client, monkeypatch):
    monkeypatch.setattr(
        tasks_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="نتيجة مجدولة")),
    )
    monkeypatch.setattr(tasks_module, "execute_scheduled_task", None)
    token = _register_and_login(client, "scheduled-run@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, token)
    task = _create_task(client, headers, workspace["id"])

    response = client.post(
        f"/scheduled-tasks/{task['id']}/run",
        headers=headers,
    )
    assert response.status_code in {200, 202}
    run = response.json()
    assert run["scheduled_task_id"] == task["id"]

    history = client.get(
        f"/scheduled-tasks/{task['id']}/runs",
        headers=headers,
    )
    assert history.status_code == 200
    assert history.json()[0]["status"] == ScheduledTaskRunStatus.succeeded.value
    assert history.json()[0]["conversation_id"] is not None


def test_cannot_run_or_read_other_users_task_history(client):
    token_a = _register_and_login(client, "scheduled-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    workspace = _create_workspace(client, token_a, "Private")
    task = _create_task(client, headers_a, workspace["id"])

    token_b = _register_and_login(client, "scheduled-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.post(
        f"/scheduled-tasks/{task['id']}/run",
        headers=headers_b,
    ).status_code == 404
    assert client.get(
        f"/scheduled-tasks/{task['id']}/runs",
        headers=headers_b,
    ).status_code == 404


def test_failed_manual_run_is_recorded(client, monkeypatch):
    monkeypatch.setattr(
        tasks_module,
        "get_ai_reply",
        AsyncMock(side_effect=RuntimeError("provider down")),
    )
    monkeypatch.setattr(tasks_module, "execute_scheduled_task", None)
    token = _register_and_login(client, "scheduled-error@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, token)
    task = _create_task(client, headers, workspace["id"])

    response = client.post(f"/scheduled-tasks/{task['id']}/run", headers=headers)
    assert response.status_code in {200, 202}
    run = response.json()

    history = client.get(
        f"/scheduled-tasks/{task['id']}/runs",
        headers=headers,
    ).json()
    assert history[0]["status"] == ScheduledTaskRunStatus.failed.value
    assert "provider down" in history[0]["error"]


def test_scheduled_agent_creates_persistent_agent_job(client, db_session, monkeypatch):
    token = _register_and_login(client, "scheduled-agent@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, token)
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    created = client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace["id"],
            "prompt": "شغّل وكيلًا لتحليل المهمة",
            "schedule_type": "once",
            "execution_mode": "agent",
            "next_run_at": future,
        },
        headers=headers,
    )
    assert created.status_code == 201

    task = db_session.get(ScheduledTask, created.json()["id"])
    fake_job_ids = []

    class FakeAgentTask:
        def delay(self, job_id):
            fake_job_ids.append(job_id)

    monkeypatch.setattr(tasks_module, "execute_agent_job", FakeAgentTask())

    run = ScheduledTaskRun(
        scheduled_task_id=task.id,
        user_id=task.user_id,
        workspace_id=task.workspace_id,
        prompt=task.prompt,
        scheduled_for=task.next_run_at,
    )
    db_session.add(run)
    db_session.flush()

    tasks_module._execute_scheduled_task(task.id, run.id, db=db_session)

    job = db_session.get(AgentJob, fake_job_ids[0])
    db_session.refresh(run)
    db_session.refresh(task)

    assert job is not None
    assert job.status == "queued"
    assert run.agent_job_id == job.id
    assert run.conversation_id == job.conversation_id
    assert run.status == ScheduledTaskRunStatus.queued
    assert task.is_active is False
