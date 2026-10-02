"""Tests for persistent multi-step Agent workflows."""

from types import SimpleNamespace

from app import services
from app import tasks as tasks_module
from app.models.agent_workflow import AgentWorkflow


class _FakeCelery:
    def __init__(self):
        self.calls = []

    def send_task(self, name, args):
        self.calls.append((name, args))
        return SimpleNamespace(id="workflow-task-1")


def _register_and_login(client, email):
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    response = client.post("/auth/login", json={"email": email, "password": "StrongPass123"})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _workspace_and_project(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    workspace = client.post("/workspaces", json={"name": "WF Workspace"}, headers=headers)
    assert workspace.status_code == 201
    project = client.post(
        "/projects",
        json={"workspace_id": workspace.json()["id"], "name": "Workflow Project"},
        headers=headers,
    )
    assert project.status_code == 201
    return workspace.json(), project.json()


def test_create_and_list_workflow_with_steps(client, monkeypatch):
    token = _register_and_login(client, "workflow-create@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace, project = _workspace_and_project(client, token)

    import app.routers.agent_workflows as router_module

    fake_celery = _FakeCelery()
    monkeypatch.setattr(router_module, "celery_app", fake_celery)

    response = client.post(
        "/agent-workflows",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "name": "Build and verify",
            "steps": [
                {"name": "Plan", "instruction": "حدد خطة التنفيذ."},
                {"name": "Implement", "instruction": "نفذ الخطة."},
                {"name": "Verify", "instruction": "تحقق من النتيجة."},
            ],
        },
        headers=headers,
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert len(payload["steps"]) == 3
    assert payload["steps"][0]["position"] == 1
    assert payload["steps"][2]["position"] == 3
    assert fake_celery.calls == [("execute_agent_workflow", [payload["id"]])]

    listed = client.get("/agent-workflows", params={"project_id": project["id"]}, headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == payload["id"]


def test_workflow_isolation_and_resume_from_failed_step(client, db_session, monkeypatch):
    token = _register_and_login(client, "workflow-resume@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace, project = _workspace_and_project(client, token)

    import app.routers.agent_workflows as router_module

    fake_celery = _FakeCelery()
    monkeypatch.setattr(router_module, "celery_app", fake_celery)

    created = client.post(
        "/agent-workflows",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "name": "Resume me",
            "steps": [
                {"name": "Step one", "instruction": "نفذ الأولى."},
                {"name": "Step two", "instruction": "نفذ الثانية."},
            ],
        },
        headers=headers,
    )
    assert created.status_code == 202
    workflow_id = created.json()["id"]

    owner = client.get(f"/agent-workflows/{workflow_id}", headers=headers)
    assert owner.status_code == 200

    other_token = _register_and_login(client, "workflow-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    assert client.get(f"/agent-workflows/{workflow_id}", headers=other_headers).status_code == 404

    workflow = owner.json()
    assert workflow["status"] == "queued"

    stored = db_session.get(AgentWorkflow, workflow_id)
    stored.status = "failed"
    stored.current_step_position = 2
    stored.steps[0].status = "succeeded"
    stored.steps[0].result_text = "خطة محفوظة"
    stored.steps[1].status = "failed"
    db_session.commit()

    resumed = client.post(f"/agent-workflows/{workflow_id}/resume", headers=headers)
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "queued"
    assert fake_celery.calls[-1] == ("execute_agent_workflow", [workflow_id])


def test_execute_workflow_persists_step_checkpoints(client, db_session, monkeypatch):
    token = _register_and_login(client, "workflow-execute@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace, project = _workspace_and_project(client, token)

    import app.routers.agent_workflows as router_module

    fake_celery = _FakeCelery()
    monkeypatch.setattr(router_module, "celery_app", fake_celery)

    created = client.post(
        "/agent-workflows",
        json={
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "name": "Execute workflow",
            "steps": [
                {"name": "Plan", "instruction": "خطط."},
                {"name": "Verify", "instruction": "تحقق."},
            ],
        },
        headers=headers,
    )
    workflow_id = created.json()["id"]

    class FakeProvider:
        name = "fake"

    results = iter(
        [
            SimpleNamespace(
                run_id="wf-run-1",
                status="completed",
                text="الخطة",
                sources=[],
                input_tokens=5,
                output_tokens=3,
            ),
            SimpleNamespace(
                run_id="wf-run-2",
                status="completed",
                text="تم التحقق",
                sources=[],
                input_tokens=6,
                output_tokens=4,
            ),
        ]
    )

    class FakeRuntime:
        def __init__(self, provider, event_sink):
            self.event_sink = event_sink

        async def run(self, **kwargs):
            await self.event_sink({"type": "runtime_start"})
            return next(results)

    monkeypatch.setattr("app.services.agent_workflow.get_provider", lambda model: FakeProvider())
    monkeypatch.setattr("app.services.agent_workflow.AgentRuntime", FakeRuntime)
    monkeypatch.setattr(
        "app.services.agent_workflow.get_daily_ai_limit",
        lambda user, db: 100,
    )

    import app.services.agent_workflow as workflow_service
    workflow_service.execute_agent_workflow(workflow_id, db=db_session)

    db_session.expire_all()
    workflow = db_session.get(AgentWorkflow, workflow_id)
    assert workflow.status == "succeeded"
    assert workflow.current_step_position == 2
    assert workflow.checkpoint["last_completed_step_position"] == 2
    assert workflow.checkpoint["completed_steps"] == [1, 2]
    assert [step.status for step in workflow.steps] == ["succeeded", "succeeded"]
    assert [step.run_id for step in workflow.steps] == ["wf-run-1", "wf-run-2"]
