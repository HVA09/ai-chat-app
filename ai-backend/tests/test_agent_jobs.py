"""Tests for persistent long-running Agent jobs."""

from datetime import datetime, timezone
from types import SimpleNamespace

from app import tasks as tasks_module
from app.models.agent_job import AgentJob
from app.models.agent_workflow_step import AgentWorkflowStep


class _FakeAgentTask:
    def __init__(self):
        self.calls = []

    def delay(self, job_id):
        self.calls.append(job_id)
        return SimpleNamespace(id=f"celery-{job_id}")


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _create_workspace(client, token):
    response = client.post(
        "/workspaces",
        json={"name": "Agent Jobs"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_create_agent_job_returns_accepted_without_running_inline(client, monkeypatch):
    token = _register_and_login(client, "agent-job-create@example.com")
    workspace = _create_workspace(client, token)
    headers = {"Authorization": f"Bearer {token}"}
    fake_task = _FakeAgentTask()

    import app.routers.agent_jobs as agent_jobs_router

    monkeypatch.setattr(agent_jobs_router, "execute_agent_job", fake_task)
    monkeypatch.setattr(agent_jobs_router, "celery_app", object())

    response = client.post(
        "/agent-jobs",
        json={
            "workspace_id": workspace["id"],
            "task": "حلّل هذه المهمة كوكيل مستقل",
        },
        headers=headers,
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["celery_task_id"] == "celery-" + str(payload["id"])
    assert payload["agent_version"].startswith("agent-1-")
    assert payload["tool_policy_snapshot"]["allowed_tools"]
    assert fake_task.calls == [payload["id"]]

    fetched = client.get(f"/agent-jobs/{payload['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["conversation_id"] is not None


def test_agent_job_isolation_and_cooperative_cancel(client, monkeypatch):
    token_a = _register_and_login(client, "agent-job-owner@example.com")
    workspace = _create_workspace(client, token_a)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    fake_task = _FakeAgentTask()

    import app.routers.agent_jobs as agent_jobs_router

    monkeypatch.setattr(agent_jobs_router, "execute_agent_job", fake_task)
    monkeypatch.setattr(agent_jobs_router, "celery_app", object())

    created = client.post(
        "/agent-jobs",
        json={"workspace_id": workspace["id"], "task": "مهمة خاصة"},
        headers=headers_a,
    )
    assert created.status_code == 202
    job_id = created.json()["id"]

    token_b = _register_and_login(client, "agent-job-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    assert client.get(f"/agent-jobs/{job_id}", headers=headers_b).status_code == 404

    cancelled = client.post(
        f"/agent-jobs/{job_id}/cancel",
        headers=headers_a,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancel_requested"] is True


def test_execute_agent_job_persists_success(client, db_session, monkeypatch):
    token = _register_and_login(client, "agent-job-execute@example.com")
    workspace = _create_workspace(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    import app.routers.agent_jobs as agent_jobs_router

    fake_task = _FakeAgentTask()
    monkeypatch.setattr(agent_jobs_router, "execute_agent_job", fake_task)
    monkeypatch.setattr(agent_jobs_router, "celery_app", object())

    created = client.post(
        "/agent-jobs",
        json={"workspace_id": workspace["id"], "task": "نفذ المهمة بنجاح"},
        headers=headers,
    )
    assert created.status_code == 202
    job_id = created.json()["id"]

    class FakeProvider:
        name = "fake"

    class FakeResult:
        run_id = "run-123"
        status = "completed"
        text = "تم التنفيذ"
        sources = [{"id": "job"}]
        input_tokens = 12
        output_tokens = 8

    class FakeRuntime:
        def __init__(self, provider, event_sink):
            self.provider = provider
            self.event_sink = event_sink

        async def run(self, **kwargs):
            await self.event_sink({"type": "runtime_start"})
            return FakeResult()

    monkeypatch.setattr(tasks_module, "get_provider", lambda model: FakeProvider())
    monkeypatch.setattr(tasks_module, "AgentRuntime", FakeRuntime)
    monkeypatch.setattr(tasks_module, "get_daily_ai_limit", lambda user, db: 100)

    tasks_module._execute_agent_job(job_id, db=db_session)

    db_session.expire_all()
    job = db_session.get(AgentJob, job_id)
    assert job.status == "succeeded"
    assert job.run_id == "run-123"
    assert job.result_text == "تم التنفيذ"
    assert job.input_tokens == 12
    assert job.output_tokens == 8
    assert job.finished_at is not None


def test_create_agent_job_persists_workflow_steps(client, monkeypatch):
    token = _register_and_login(client, "agent-workflow-create@example.com")
    workspace = _create_workspace(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    import app.routers.agent_jobs as agent_jobs_router
    fake_task = _FakeAgentTask()
    monkeypatch.setattr(agent_jobs_router, "execute_agent_job", fake_task)
    monkeypatch.setattr(agent_jobs_router, "celery_app", object())

    response = client.post(
        "/agent-jobs",
        json={
            "workspace_id": workspace["id"],
            "task": "بناء خطة مشروع",
            "workflow_steps": [
                {"title": "تحليل", "prompt": "حلّل المتطلبات"},
                {"title": "تنفيذ", "prompt": "اكتب خطة التنفيذ"},
            ],
        },
        headers=headers,
    )
    assert response.status_code == 202
    payload = response.json()
    assert [step["sequence"] for step in payload["workflow_steps"]] == [1, 2]
    assert [step["title"] for step in payload["workflow_steps"]] == ["تحليل", "تنفيذ"]
    assert all(step["status"] == "queued" for step in payload["workflow_steps"])


def test_agent_workflow_persists_checkpoints_and_resume_skips_completed_steps(
    client, db_session, monkeypatch
):
    token = _register_and_login(client, "agent-workflow-resume@example.com")
    workspace = _create_workspace(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    import app.routers.agent_jobs as agent_jobs_router

    fake_task = _FakeAgentTask()
    monkeypatch.setattr(agent_jobs_router, "execute_agent_job", fake_task)
    monkeypatch.setattr(agent_jobs_router, "celery_app", object())

    created = client.post(
        "/agent-jobs",
        json={
            "workspace_id": workspace["id"],
            "task": "workflow test",
            "workflow_steps": [
                {"title": "الأولى", "prompt": "نفذ الأولى"},
                {"title": "الثانية", "prompt": "نفذ الثانية"},
                {"title": "الثالثة", "prompt": "نفذ الثالثة"},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 202
    job_id = created.json()["id"]

    class FakeProvider:
        name = "fake"

    class FakeResult:
        def __init__(self, run_id, status, text):
            self.run_id = run_id
            self.status = status
            self.text = text
            self.sources = [{"id": run_id}]
            self.input_tokens = 4
            self.output_tokens = 6

    calls = []

    class FakeRuntime:
        def __init__(self, provider, event_sink):
            self.provider = provider
            self.event_sink = event_sink

        async def run(self, *, task, history, conversation, current_user, db):
            calls.append(task)
            if task == "نفذ الثانية" and calls.count(task) == 1:
                return FakeResult("run-2-failed", "stopped", "توقفت الثانية")
            return FakeResult(f"run-{len(calls)}", "completed", f"نتيجة {task}")

    monkeypatch.setattr(tasks_module, "get_provider", lambda model: FakeProvider())
    monkeypatch.setattr(tasks_module, "AgentRuntime", FakeRuntime)
    monkeypatch.setattr(tasks_module, "get_daily_ai_limit", lambda user, db: 100)

    tasks_module._execute_agent_job(job_id, db=db_session)

    db_session.expire_all()
    steps = (
        db_session.query(AgentWorkflowStep)
        .filter(AgentWorkflowStep.agent_job_id == job_id)
        .order_by(AgentWorkflowStep.sequence.asc())
        .all()
    )
    assert [step.status for step in steps] == ["succeeded", "failed", "queued"]
    assert steps[0].checkpoint["status"] == "succeeded"
    assert steps[0].attempt_count == 1
    assert calls == ["نفذ الأولى", "نفذ الثانية"]

    resumed = client.post(f"/agent-jobs/{job_id}/resume", headers=headers)
    assert resumed.status_code == 202
    assert resumed.json()["status"] == "queued"
    assert fake_task.calls[-1] == job_id

    tasks_module._execute_agent_job(job_id, db=db_session)

    db_session.expire_all()
    job = db_session.get(AgentJob, job_id)
    steps = (
        db_session.query(AgentWorkflowStep)
        .filter(AgentWorkflowStep.agent_job_id == job_id)
        .order_by(AgentWorkflowStep.sequence.asc())
        .all()
    )
    assert job.status == "succeeded"
    assert [step.status for step in steps] == ["succeeded", "succeeded", "succeeded"]
    assert steps[0].attempt_count == 1
    assert steps[1].attempt_count == 2
    assert steps[2].attempt_count == 1
    assert calls == ["نفذ الأولى", "نفذ الثانية", "نفذ الثالثة"]
