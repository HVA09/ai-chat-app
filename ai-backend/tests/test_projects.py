"""اختبارات مشاريع مساحات العمل."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email: str, password: str = "StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _create_workspace(client, headers, name="Workspace"):
    response = client.post("/workspaces", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()


def _create_assistant(client, headers, name="Assistant", instructions="Help clearly."):
    response = client.post(
        "/assistants",
        json={
            "name": name,
            "instructions": instructions,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_project_crud_and_conversation_filter(client, monkeypatch):
    token = _register_and_login(client, "project@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    created = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "Study",
            "description": "Study project",
            "instructions": "Answer in Arabic and use practical examples.",
        },
        headers=headers,
    )
    assert created.status_code == 201
    project = created.json()
    assert project["instructions"] == "Answer in Arabic and use practical examples."

    listed = client.get(
        "/projects",
        params={"workspace_id": workspace["id"]},
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == project["id"]

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    conversation = client.post(
        "/chat",
        json={"message": "رسالة", "workspace_id": workspace["id"]},
        headers=headers,
    )
    assert conversation.status_code == 200
    conversation_id = conversation.json()["conversation_id"]

    moved = client.patch(
        f"/conversations/{conversation_id}/project",
        json={"project_id": project["id"]},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["project_id"] == project["id"]

    filtered = client.get(
        "/conversations",
        params={"workspace_id": workspace["id"], "project_id": project["id"]},
        headers=headers,
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [conversation_id]

    updated = client.patch(
        f"/projects/{project['id']}",
        json={
            "name": "Study 2",
            "description": "Updated",
            "instructions": "Keep replies concise and structured.",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Study 2"
    assert updated.json()["instructions"] == "Keep replies concise and structured."

    removed = client.delete(f"/projects/{project['id']}", headers=headers)
    assert removed.status_code == 204
    assert client.get(
        f"/projects",
        params={"workspace_id": workspace["id"]},
        headers=headers,
    ).json() == []


def test_cannot_move_conversation_to_other_workspace_project(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    owner_token = _register_and_login(client, "project-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace_a = _create_workspace(client, owner_headers, "A")

    other_token = _register_and_login(client, "project-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    workspace_b = _create_workspace(client, other_headers, "B")

    project = client.post(
        "/projects",
        json={"workspace_id": workspace_b["id"], "name": "Private"},
        headers=other_headers,
    ).json()

    conversation = client.post(
        "/chat",
        json={"message": "رسالة", "workspace_id": workspace_a["id"]},
        headers=owner_headers,
    )
    conversation_id = conversation.json()["conversation_id"]

    response = client.patch(
        f"/conversations/{conversation_id}/project",
        json={"project_id": project["id"]},
        headers=owner_headers,
    )
    assert response.status_code == 404


def test_project_crud_isolated_across_workspaces(client):
    owner_token = _register_and_login(client, "project-isolation-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace_owner = _create_workspace(client, owner_headers, "Owner Workspace")

    other_token = _register_and_login(client, "project-isolation-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    workspace_other = _create_workspace(client, other_headers, "Other Workspace")

    project = client.post(
        "/projects",
        json={"workspace_id": workspace_other["id"], "name": "Private"},
        headers=other_headers,
    ).json()

    assert client.get(
        "/projects",
        params={"workspace_id": workspace_other["id"]},
        headers=owner_headers,
    ).status_code == 404

    assert client.patch(
        f"/projects/{project['id']}",
        json={
            "name": "Hijacked",
            "description": None,
            "instructions": None,
        },
        headers=owner_headers,
    ).status_code == 404

    assert client.delete(
        f"/projects/{project['id']}",
        headers=owner_headers,
    ).status_code == 404

    own = client.get(
        "/projects",
        params={"workspace_id": workspace_owner["id"]},
        headers=owner_headers,
    )
    assert own.status_code == 200
    assert all(item["id"] != project["id"] for item in own.json())


def test_project_instructions_are_applied_to_chat(client, monkeypatch):
    token = _register_and_login(client, "project-instructions@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    project = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "Python",
            "instructions": "Explain in Arabic, step by step, with one exercise.",
        },
        headers=headers,
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    captured = {}

    async def fake_get_ai_reply(message, history, model):
        captured["message"] = message
        captured["history"] = history
        captured["model"] = model
        return AIReply(text="رد")

    monkeypatch.setattr(chat_router_module, "get_ai_reply", fake_get_ai_reply)

    response = client.post(
        "/chat",
        json={
            "message": "اشرح المتغيرات",
            "workspace_id": workspace["id"],
            "project_id": project_id,
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert "[PROJECT INSTRUCTIONS]" in captured["message"]
    assert "Explain in Arabic, step by step, with one exercise." in captured["message"]


def test_project_instructions_are_scoped_to_project(client, monkeypatch):
    token = _register_and_login(client, "project-instructions-scope@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    first = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "A",
            "instructions": "Private project guidance A",
        },
        headers=headers,
    ).json()
    second = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "B",
            "instructions": "Private project guidance B",
        },
        headers=headers,
    ).json()

    captured = []
    async def fake_get_ai_reply(message, history, model):
        captured.append(message)
        return AIReply(text="رد")

    monkeypatch.setattr(chat_router_module, "get_ai_reply", fake_get_ai_reply)

    response_a = client.post(
        "/chat",
        json={
            "message": "سؤال A",
            "workspace_id": workspace["id"],
            "project_id": first["id"],
        },
        headers=headers,
    )
    assert response_a.status_code == 200
    assert "Private project guidance A" in captured[-1]
    assert "Private project guidance B" not in captured[-1]

    response_none = client.post(
        "/chat",
        json={
            "message": "سؤال عام",
            "workspace_id": workspace["id"],
        },
        headers=headers,
    )
    assert response_none.status_code == 200
    assert "Private project guidance A" not in captured[-1]
    assert "Private project guidance B" not in captured[-1]

    response_b = client.post(
        "/chat",
        json={
            "message": "سؤال B",
            "workspace_id": workspace["id"],
            "project_id": second["id"],
        },
        headers=headers,
    )
    assert response_b.status_code == 200
    assert "Private project guidance B" in captured[-1]
    assert "Private project guidance A" not in captured[-1]


def test_project_default_assistant_is_used_and_explicit_override_wins(client, monkeypatch):
    token = _register_and_login(client, "project-assistant@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers)

    default_assistant = _create_assistant(
        client,
        headers,
        name="Project Helper",
        instructions="Always explain project work step by step.",
    )
    explicit_assistant = _create_assistant(
        client,
        headers,
        name="Explicit Helper",
        instructions="Use concise answers.",
    )

    created = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "Python",
            "assistant_id": default_assistant["id"],
        },
        headers=headers,
    )
    assert created.status_code == 201
    project = created.json()
    assert project["assistant_id"] == default_assistant["id"]

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )

    implicit = client.post(
        "/chat",
        json={
            "message": "سؤال المشروع",
            "workspace_id": workspace["id"],
            "project_id": project["id"],
        },
        headers=headers,
    )
    assert implicit.status_code == 200
    implicit_id = implicit.json()["conversation_id"]
    implicit_detail = client.get(
        f"/conversations/{implicit_id}",
        headers=headers,
    )
    assert implicit_detail.status_code == 200
    assert implicit_detail.json()["assistant_id"] == default_assistant["id"]

    explicit = client.post(
        "/chat",
        json={
            "message": "سؤال صريح",
            "workspace_id": workspace["id"],
            "project_id": project["id"],
            "assistant_id": explicit_assistant["id"],
        },
        headers=headers,
    )
    assert explicit.status_code == 200
    explicit_id = explicit.json()["conversation_id"]
    explicit_detail = client.get(
        f"/conversations/{explicit_id}",
        headers=headers,
    )
    assert explicit_detail.status_code == 200
    assert explicit_detail.json()["assistant_id"] == explicit_assistant["id"]


def test_project_rejects_inaccessible_default_assistant(client):
    owner_token = _register_and_login(client, "project-assistant-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _create_workspace(client, owner_headers)

    other_token = _register_and_login(client, "project-assistant-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    other_assistant = _create_assistant(client, other_headers, name="Private")

    response = client.post(
        "/projects",
        json={
            "workspace_id": workspace["id"],
            "name": "Private Project",
            "assistant_id": other_assistant["id"],
        },
        headers=owner_headers,
    )
    assert response.status_code == 404

def test_project_validation_reports_manifest_errors_and_secret_warnings(client):
    token = _register_and_login(client, "project-validation@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers, "Validation")
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Broken App"},
        headers=headers,
    ).json()

    files = [
        ("package.json", '{"name":'),
        (".env", "API_KEY=secret"),
        ("index.html", "<div>missing roots</div>"),
    ]
    for path, content in files:
        response = client.post(
            f"/projects/{project['id']}/files",
            json={"path": path, "content": content},
            headers=headers,
        )
        assert response.status_code == 201

    response = client.get(
        f"/projects/{project['id']}/validate",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["project_kind"] == "javascript"
    assert data["files_count"] == 3
    assert data["errors"] == 1
    assert data["warnings"] >= 3
    codes = {item["code"] for item in data["checks"]}
    assert "invalid_package_json" in codes
    assert "secret_file_name" in codes
    assert "html_root_missing" in codes


def test_project_validation_isolated_to_workspace_members(client):
    owner_token = _register_and_login(client, "project-validation-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner_workspace = _create_workspace(client, owner_headers, "Owner")
    project = client.post(
        "/projects",
        json={"workspace_id": owner_workspace["id"], "name": "Private"},
        headers=owner_headers,
    ).json()

    outsider_token = _register_and_login(client, "project-validation-outsider@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    response = client.get(
        f"/projects/{project['id']}/validate",
        headers=outsider_headers,
    )
    assert response.status_code == 404




def test_project_preview_plan_selects_static_html(client):
    token = _register_and_login(client, "project-preview-static@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers, "Preview Static")
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Static"},
        headers=headers,
    ).json()

    response = client.post(
        f"/projects/{project['id']}/files",
        json={
            "path": "index.html",
            "content": "<html><body><h1>Preview</h1></body></html>",
        },
        headers=headers,
    )
    assert response.status_code == 201

    plan = client.get(
        f"/projects/{project['id']}/preview-plan",
        headers=headers,
    )
    assert plan.status_code == 200
    data = plan.json()
    assert data["strategy"] == "static-html"
    assert data["status"] == "ready"
    assert data["entrypoint"] == "index.html"


def test_project_preview_plan_never_executes_javascript_build(client):
    token = _register_and_login(client, "project-preview-js@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers, "Preview JS")
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "React App"},
        headers=headers,
    ).json()

    for path, content in (
        (
            "package.json",
            '{"name":"demo","scripts":{"build":"node malicious-build.js"}}',
        ),
        ("src/main.jsx", "console.log('hello');"),
    ):
        response = client.post(
            f"/projects/{project['id']}/files",
            json={"path": path, "content": content},
            headers=headers,
        )
        assert response.status_code == 201

    plan = client.get(
        f"/projects/{project['id']}/preview-plan",
        headers=headers,
    )
    assert plan.status_code == 200
    data = plan.json()
    assert data["strategy"] == "javascript-build"
    assert data["status"] == "build-required"
    assert data["build_command_detected"] is True
    assert data["entrypoint"] == "package.json"


def test_project_preview_plan_isolated_from_other_workspace(client):
    owner_token = _register_and_login(client, "project-preview-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _create_workspace(client, owner_headers, "Preview Owner")
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Private"},
        headers=owner_headers,
    ).json()

    outsider_token = _register_and_login(client, "project-preview-outsider@example.com")
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    response = client.get(
        f"/projects/{project['id']}/preview-plan",
        headers=outsider_headers,
    )
    assert response.status_code == 404


def test_project_name_conflicts_are_case_insensitive(client):
    token = _register_and_login(client, "project-name-conflict@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers, "Conflict Workspace")

    first = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Portable"},
        headers=headers,
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": " portable "},
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "يوجد مشروع بهذا الاسم في مساحة العمل"


def test_project_delete_keeps_uploaded_files_private_to_uploader(
    client, db_session, tmp_path, monkeypatch
):
    """Deleting a project must not promote its uploads to shared workspace files."""
    from app.config import settings as app_settings
    from app.models.file_attachment import FileAttachment
    from app.models.user import User
    from app.models.workspace import WorkspaceMember, WorkspaceRole
    from app.routers import files as files_router

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    for setting_name in (
        "S3_BUCKET",
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setattr(app_settings, setting_name, "")
    monkeypatch.setattr(files_router, "index_file_chunks", lambda _db, _file: 0)

    owner_token = _register_and_login(client, "project-delete-file-owner@example.com")
    member_token = _register_and_login(client, "project-delete-workspace-member@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    member_headers = {"Authorization": f"Bearer {member_token}"}

    workspace = _create_workspace(client, owner_headers, name="Private project files")
    member = (
        db_session.query(User)
        .filter(User.email == "project-delete-workspace-member@example.com")
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

    created_project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Confidential project"},
        headers=owner_headers,
    )
    assert created_project.status_code == 201
    project_id = created_project.json()["id"]

    uploaded = client.post(
        "/files/upload",
        params={"project_id": project_id},
        files={
            "file": (
                "project-secret.txt",
                b"Information that must remain private after project deletion.",
                "text/plain",
            )
        },
        headers=owner_headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]
    assert uploaded.json()["project_id"] == project_id
    assert uploaded.json()["workspace_id"] == workspace["id"]

    member_before = client.get(
        "/files",
        params={"workspace_id": workspace["id"]},
        headers=member_headers,
    )
    assert member_before.status_code == 200
    assert file_id not in {item["id"] for item in member_before.json()}

    deleted = client.delete(f"/projects/{project_id}", headers=owner_headers)
    assert deleted.status_code == 204

    db_session.expire_all()
    saved_file = db_session.get(FileAttachment, file_id)
    assert saved_file is not None
    assert saved_file.project_id is None
    assert saved_file.workspace_id is None
    assert saved_file.user_id == (
        db_session.query(User)
        .filter(User.email == "project-delete-file-owner@example.com")
        .one()
        .id
    )

    member_after = client.get(
        "/files",
        params={"workspace_id": workspace["id"]},
        headers=member_headers,
    )
    assert member_after.status_code == 200
    assert file_id not in {item["id"] for item in member_after.json()}
    assert client.get(f"/files/{file_id}", headers=member_headers).status_code == 404

    owner_personal_files = client.get("/files", headers=owner_headers)
    assert owner_personal_files.status_code == 200
    assert file_id in {item["id"] for item in owner_personal_files.json()}
    owner_download = client.get(f"/files/{file_id}", headers=owner_headers)
    assert owner_download.status_code == 200
    assert b"Information that must remain private" in owner_download.content
