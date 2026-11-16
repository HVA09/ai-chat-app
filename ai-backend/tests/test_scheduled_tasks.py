"""اختبارات المهام المجدولة."""
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.scheduled_task import ScheduledTask
from app.models.scheduled_task_run import ScheduledTaskRun

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
            "execution_mode": "standard",
            "next_run_at": future,
        },
        headers=headers,
    )
    assert created.status_code == 201
    task = created.json()
    assert task["is_active"] is True
    assert task["execution_mode"] == "standard"

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


def test_scheduled_run_slot_is_unique(client, db_session):
    token = _register_and_login(client, "schedule-idempotency@example.com")
    workspace = _create_workspace(client, token, "Idempotency")
    headers = {"Authorization": f"Bearer {token}"}
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace["id"],
            "prompt": "مهمة لا يجب تكرارها",
            "schedule_type": "daily",
            "next_run_at": future,
        },
        headers=headers,
    )
    assert response.status_code == 201

    task = db_session.query(ScheduledTask).filter(ScheduledTask.id == response.json()["id"]).one()
    scheduled_for = task.next_run_at

    db_session.add(
        ScheduledTaskRun(
            scheduled_task_id=task.id,
            user_id=task.user_id,
            workspace_id=task.workspace_id,
            prompt=task.prompt,
            scheduled_for=scheduled_for,
        )
    )
    db_session.commit()

    duplicate = ScheduledTaskRun(
        scheduled_task_id=task.id,
        user_id=task.user_id,
        workspace_id=task.workspace_id,
        prompt=task.prompt,
        scheduled_for=scheduled_for,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_workspace_member_without_scheduled_task_permission_is_denied(
    client, db_session
):
    from app.models.user import User
    from app.models.workspace import WorkspaceMember, WorkspaceRole

    owner_token = _register_and_login(client, "schedule-rbac-owner@example.com")
    workspace = _create_workspace(client, owner_token, "Schedule RBAC")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    owner_task = client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace["id"],
            "prompt": "مالك المهمة",
            "schedule_type": "once",
            "next_run_at": future,
        },
        headers=owner_headers,
    )
    assert owner_task.status_code == 201
    owner_task_id = owner_task.json()["id"]

    member_token = _register_and_login(client, "schedule-rbac-member@example.com")
    member = (
        db_session.query(User)
        .filter(User.email == "schedule-rbac-member@example.com")
        .one()
    )
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace["id"],
            user_id=member.id,
            role=WorkspaceRole.member,
        )
    )
    db_session.commit()
    member_headers = {"Authorization": f"Bearer {member_token}"}

    denied_create = client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace["id"],
            "prompt": "مهمة بلا صلاحية",
            "schedule_type": "once",
            "next_run_at": future,
        },
        headers=member_headers,
    )
    assert denied_create.status_code == 403

    denied_workspace_list = client.get(
        "/scheduled-tasks",
        params={"workspace_id": workspace["id"]},
        headers=member_headers,
    )
    assert denied_workspace_list.status_code == 403

    unfiltered_list = client.get("/scheduled-tasks", headers=member_headers)
    assert unfiltered_list.status_code == 200
    assert unfiltered_list.json() == []

    # Workspace membership alone does not override the existing task owner boundary.
    cannot_update_owner_task = client.patch(
        f"/scheduled-tasks/{owner_task_id}",
        json={"prompt": "تعديل غير مسموح"},
        headers=member_headers,
    )
    assert cannot_update_owner_task.status_code == 404
    cannot_read_owner_runs = client.get(
        f"/scheduled-tasks/{owner_task_id}/runs",
        headers=member_headers,
    )
    assert cannot_read_owner_runs.status_code == 404


def test_custom_scheduled_task_role_is_owner_scoped_and_revocable(
    client, db_session, monkeypatch
):
    from app.models.scheduled_task_run import ScheduledTaskRunStatus
    from app.models.user import User
    from app.models.workspace import WorkspaceMember, WorkspaceRole
    from app.models.workspace_rbac import WorkspaceRBACPermission, WorkspaceRBACRole

    owner_token = _register_and_login(client, "schedule-custom-owner@example.com")
    workspace = _create_workspace(client, owner_token, "Custom schedule role")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    owner_task_response = client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace["id"],
            "prompt": "مهمة المالك",
            "schedule_type": "once",
            "next_run_at": future,
        },
        headers=owner_headers,
    )
    assert owner_task_response.status_code == 201
    owner_task_id = owner_task_response.json()["id"]

    manager_token = _register_and_login(
        client, "schedule-custom-manager@example.com"
    )
    owner = (
        db_session.query(User)
        .filter(User.email == "schedule-custom-owner@example.com")
        .one()
    )
    manager = (
        db_session.query(User)
        .filter(User.email == "schedule-custom-manager@example.com")
        .one()
    )
    custom_role = WorkspaceRBACRole(
        workspace_id=workspace["id"],
        name="Scheduled task manager",
        description="Manage own scheduled tasks in this workspace",
        created_by_user_id=owner.id,
    )
    custom_role.permissions.append(
        WorkspaceRBACPermission(permission="scheduled_tasks.manage")
    )
    membership = WorkspaceMember(
        workspace_id=workspace["id"],
        user_id=manager.id,
        role=WorkspaceRole.member,
        rbac_role=custom_role,
    )
    db_session.add_all([custom_role, membership])
    db_session.commit()
    manager_headers = {"Authorization": f"Bearer {manager_token}"}

    manager_task_response = client.post(
        "/scheduled-tasks",
        json={
            "workspace_id": workspace["id"],
            "prompt": "مهمة العضو المخول",
            "schedule_type": "daily",
            "next_run_at": future,
        },
        headers=manager_headers,
    )
    assert manager_task_response.status_code == 201
    manager_task_id = manager_task_response.json()["id"]
    assert manager_task_id != owner_task_id

    listed = client.get(
        "/scheduled-tasks",
        params={"workspace_id": workspace["id"]},
        headers=manager_headers,
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [manager_task_id]

    updated = client.patch(
        f"/scheduled-tasks/{manager_task_id}",
        json={"prompt": "مهمة العضو بعد التعديل"},
        headers=manager_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["prompt"] == "مهمة العضو بعد التعديل"

    cannot_update_owner_task = client.patch(
        f"/scheduled-tasks/{owner_task_id}",
        json={"prompt": "محاولة تعديل مهمة المالك"},
        headers=manager_headers,
    )
    assert cannot_update_owner_task.status_code == 404
    cannot_run_owner_task = client.post(
        f"/scheduled-tasks/{owner_task_id}/run",
        headers=manager_headers,
    )
    assert cannot_run_owner_task.status_code == 404

    class FakeScheduledTaskQueue:
        def __init__(self):
            self.calls = []

        def delay(self, task_id, run_id):
            self.calls.append((task_id, run_id))
            return None

    fake_queue = FakeScheduledTaskQueue()
    monkeypatch.setattr("app.tasks.execute_scheduled_task", fake_queue)

    run_response = client.post(
        f"/scheduled-tasks/{manager_task_id}/run",
        headers=manager_headers,
    )
    assert run_response.status_code == 202
    assert run_response.json()["status"] == "queued"
    assert fake_queue.calls == [(manager_task_id, run_response.json()["id"])]

    db_session.add(
        ScheduledTaskRun(
            scheduled_task_id=manager_task_id,
            user_id=manager.id,
            workspace_id=workspace["id"],
            prompt="فشل سابق لإعادة المحاولة",
            status=ScheduledTaskRunStatus.failed,
        )
    )
    db_session.commit()
    db_session.expire_all()
    failed_run = (
        db_session.query(ScheduledTaskRun)
        .filter(
            ScheduledTaskRun.scheduled_task_id == manager_task_id,
            ScheduledTaskRun.status == ScheduledTaskRunStatus.failed,
        )
        .one()
    )

    retry_response = client.post(
        f"/scheduled-tasks/{manager_task_id}/runs/{failed_run.id}/retry",
        headers=manager_headers,
    )
    assert retry_response.status_code == 202
    assert fake_queue.calls[-1][0] == manager_task_id
    assert fake_queue.calls[-1][1] == retry_response.json()["id"]

    runs = client.get(
        f"/scheduled-tasks/{manager_task_id}/runs",
        headers=manager_headers,
    )
    assert runs.status_code == 200
    assert {item["id"] for item in runs.json()} >= {
        run_response.json()["id"],
        failed_run.id,
        retry_response.json()["id"],
    }

    # The next request must observe revoked RBAC permission without a cached grant.
    db_session.expire_all()
    permission = (
        db_session.query(WorkspaceRBACPermission)
        .filter(
            WorkspaceRBACPermission.role_id == custom_role.id,
            WorkspaceRBACPermission.permission == "scheduled_tasks.manage",
        )
        .one()
    )
    db_session.delete(permission)
    db_session.commit()
    db_session.expire_all()

    denied_list = client.get(
        "/scheduled-tasks",
        params={"workspace_id": workspace["id"]},
        headers=manager_headers,
    )
    assert denied_list.status_code == 403
    assert client.get("/scheduled-tasks", headers=manager_headers).json() == []

    denied_update = client.patch(
        f"/scheduled-tasks/{manager_task_id}",
        json={"is_active": False},
        headers=manager_headers,
    )
    assert denied_update.status_code == 403
    denied_run_history = client.get(
        f"/scheduled-tasks/{manager_task_id}/runs",
        headers=manager_headers,
    )
    assert denied_run_history.status_code == 403
    denied_run_now = client.post(
        f"/scheduled-tasks/{manager_task_id}/run",
        headers=manager_headers,
    )
    assert denied_run_now.status_code == 403
    denied_retry = client.post(
        f"/scheduled-tasks/{manager_task_id}/runs/{failed_run.id}/retry",
        headers=manager_headers,
    )
    assert denied_retry.status_code == 403
    denied_delete = client.delete(
        f"/scheduled-tasks/{manager_task_id}",
        headers=manager_headers,
    )
    assert denied_delete.status_code == 403
