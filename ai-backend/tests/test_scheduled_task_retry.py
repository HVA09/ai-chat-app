"""اختبارات إعادة محاولة تنفيذ مهمة مجدولة فاشلة."""
from datetime import datetime, timedelta, timezone

from app.models.scheduled_task import ScheduledTask
from app.models.scheduled_task_run import ScheduledTaskRun, ScheduledTaskRunStatus


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


def test_retry_failed_run(client, db_session):
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

    task = db_session.get(ScheduledTask, task_id)
    failed_run = ScheduledTaskRun(
        scheduled_task_id=task.id,
        user_id=task.user_id,
        workspace_id=workspace["id"],
        prompt=task.prompt,
        status=ScheduledTaskRunStatus.failed,
        error="فشل تجريبي",
    )
    db_session.add(failed_run)
    db_session.commit()
    db_session.refresh(failed_run)

    retry = client.post(
        f"/scheduled-tasks/{task_id}/runs/{failed_run.id}/retry",
        headers=headers,
    )
    assert retry.status_code == 202
    assert retry.json()["scheduled_task_id"] == task_id
