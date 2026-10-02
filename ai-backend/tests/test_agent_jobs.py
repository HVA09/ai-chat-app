"""Tests for persistent long-running Agent jobs."""

from datetime import datetime, timezone
from types import SimpleNamespace

from app import tasks as tasks_module
from app.models.agent_job import AgentJob


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
    assert job.workflow_phase == "completed"
    assert job.retry_count == 0
    assert job.max_retries == 2
    assert job.checkpoint["phase"] == "completed"


def test_execute_agent_job_retries_from_checkpoint_then_succeeds(client, db_session, monkeypatch):
    token = _register_and_login(client, "agent-job-retry@example.com")
    workspace = _create_workspace(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    import app.routers.agent_jobs as agent_jobs_router

    fake_task = _FakeAgentTask()
    monkeypatch.setattr(agent_jobs_router, "execute_agent_job", fake_task)
    monkeypatch.setattr(agent_jobs_router, "celery_app", object())

    created = client.post(
        "/agent-jobs",
        json={"workspace_id": workspace["id"], "task": "أعد المحاولة عند فشل التحقق"},
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

    class FakeRuntime:
        calls = 0

        def __init__(self, provider, event_sink):
            self.provider = provider
            self.event_sink = event_sink

        async def run(self, **kwargs):
            type(self).calls += 1
            await self.event_sink({"type": "runtime_start"})
            if type(self).calls == 1:
                return FakeResult("run-failed", "failed", "")
            return FakeResult("run-success", "completed", "تم التنفيذ بعد إعادة المحاولة")

    monkeypatch.setattr(tasks_module, "get_provider", lambda model: FakeProvider())
    monkeypatch.setattr(tasks_module, "AgentRuntime", FakeRuntime)
    monkeypatch.setattr(tasks_module, "get_daily_ai_limit", lambda user, db: 100)

    tasks_module._execute_agent_job(job_id, db=db_session)

    db_session.expire_all()
    job = db_session.get(AgentJob, job_id)
    assert job.status == "succeeded"
    assert FakeRuntime.calls == 2
    assert job.retry_count == 1
    assert job.run_id == "run-success"
    assert job.result_text == "تم التنفيذ بعد إعادة المحاولة"
    assert job.input_tokens == 8
    assert job.output_tokens == 12
    assert job.workflow_phase == "completed"
    assert job.checkpoint["phase"] == "completed"
    assert job.checkpoint["attempt"] == 2


def test_execute_agent_job_does_not_retry_security_stop(client, db_session, monkeypatch):
    token = _register_and_login(client, "agent-job-stop@example.com")
    workspace = _create_workspace(client, token)
    headers = {"Authorization": f"Bearer {token}"}

    import app.routers.agent_jobs as agent_jobs_router

    fake_task = _FakeAgentTask()
    monkeypatch.setattr(agent_jobs_router, "execute_agent_job", fake_task)
    monkeypatch.setattr(agent_jobs_router, "celery_app", object())

    created = client.post(
        "/agent-jobs",
        json={"workspace_id": workspace["id"], "task": "لا تعاود بعد توقف أمني"},
        headers=headers,
    )
    assert created.status_code == 202
    job_id = created.json()["id"]

    class FakeProvider:
        name = "fake"

    class FakeResult:
        run_id = "run-stop"
        status = "stopped"
        text = "تم إيقاف التشغيل بسبب حاجز أمني"
        sources = [{"id": "security-stop"}]
        input_tokens = 3
        output_tokens = 5

    class FakeRuntime:
        calls = 0

        def __init__(self, provider, event_sink):
            self.provider = provider
            self.event_sink = event_sink

        async def run(self, **kwargs):
            type(self).calls += 1
            await self.event_sink({"type": "runtime_start"})
            return FakeResult()

    monkeypatch.setattr(tasks_module, "get_provider", lambda model: FakeProvider())
    monkeypatch.setattr(tasks_module, "AgentRuntime", FakeRuntime)
    monkeypatch.setattr(tasks_module, "get_daily_ai_limit", lambda user, db: 100)

    tasks_module._execute_agent_job(job_id, db=db_session)

    db_session.expire_all()
    job = db_session.get(AgentJob, job_id)
    assert job.status == "failed"
    assert FakeRuntime.calls == 1
    assert job.retry_count == 0
    assert job.workflow_phase == "failed"
    assert job.checkpoint["phase"] == "failed"
