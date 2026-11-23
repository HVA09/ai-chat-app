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

def test_project_delete_keeps_attachments_private_and_out_of_workspace_rag(
    client, db_session, tmp_path, monkeypatch
):
    import asyncio
    from pathlib import Path

    from app.config import settings as app_settings
    from app.models.assistant_file_link import AssistantFileLink
    from app.models.assistant_version import AssistantVersion
    from app.models.assistant_workspace_share import AssistantWorkspaceShare
    from app.models.conversation import Conversation
    from app.models.file_attachment import FileAttachment
    from app.models.file_chunk import FileChunk
    from app.models.project_memory import ProjectMemory
    from app.models.user import User
    from app.models.workspace import WorkspaceMember, WorkspaceRole
    from app.services import rag

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    for setting_name in (
        "S3_BUCKET",
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setattr(app_settings, setting_name, "")
    owner_token = _register_and_login(client, "project-delete-private-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _create_workspace(client, owner_headers, "Private retention")
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Restricted project"},
        headers=owner_headers,
    ).json()
    assistant = _create_assistant(
        client,
        owner_headers,
        name="Project knowledge assistant",
    )

    member_token = _register_and_login(client, "project-delete-private-member@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}
    owner = (
        db_session.query(User)
        .filter(User.email == "project-delete-private-owner@example.com")
        .one()
    )
    member = (
        db_session.query(User)
        .filter(User.email == "project-delete-private-member@example.com")
        .one()
    )
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace["id"],
            user_id=member.id,
            role=WorkspaceRole.member,
        )
    )

    payload = b"private project attachment"
    stored_filename = "project-private-attachment.txt"
    file_path = Path(app_settings.UPLOAD_DIR) / str(owner.id) / stored_filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(payload)
    attachment = FileAttachment(
        user_id=owner.id,
        workspace_id=workspace["id"],
        project_id=project["id"],
        original_filename="private-attachment.txt",
        stored_filename=stored_filename,
        object_key=f"users/{owner.id}/{stored_filename}",
        content_type="text/plain",
        size_bytes=len(payload),
        extracted_text="confidential project knowledge",
    )
    db_session.add(attachment)
    db_session.flush()
    db_session.add(
        FileChunk(
            file_id=attachment.id,
            chunk_index=0,
            content="confidential project knowledge",
            embedding=[0.1] * 768,
        )
    )
    db_session.add(
        AssistantFileLink(
            assistant_id=assistant["id"],
            file_id=attachment.id,
        )
    )
    historical_version = db_session.query(AssistantVersion).filter(
        AssistantVersion.assistant_id == assistant["id"],
        AssistantVersion.version == 1,
    ).one()
    historical_version.knowledge_file_ids = [attachment.id]
    db_session.add(
        AssistantWorkspaceShare(
            assistant_id=assistant["id"],
            workspace_id=workspace["id"],
            shared_by_user_id=owner.id,
        )
    )
    db_session.add(
        ProjectMemory(
            project_id=project["id"],
            created_by_user_id=owner.id,
            content="project-only memory",
        )
    )
    member_conversation = Conversation(
        user_id=member.id,
        workspace_id=workspace["id"],
        title="Workspace member conversation",
    )
    db_session.add(member_conversation)
    db_session.commit()
    file_id = attachment.id
    member_conversation_id = member_conversation.id

    deleted = client.delete(f"/projects/{project['id']}", headers=owner_headers)
    assert deleted.status_code == 204
    db_session.expire_all()

    retained = db_session.get(FileAttachment, file_id)
    assert retained is not None
    assert retained.user_id == owner.id
    assert retained.workspace_id is None
    assert retained.project_id is None
    assert db_session.query(FileChunk).filter(FileChunk.file_id == file_id).count() == 1
    assert db_session.query(AssistantFileLink).filter(
        AssistantFileLink.file_id == file_id
    ).count() == 0
    snapshot = db_session.query(AssistantVersion).filter(
        AssistantVersion.assistant_id == assistant["id"],
        AssistantVersion.version == 1,
    ).one()
    assert snapshot.knowledge_file_ids == []

    restored = client.post(
        f"/assistants/{assistant['id']}/versions/1/restore",
        headers=owner_headers,
    )
    assert restored.status_code == 200
    db_session.expire_all()
    assert db_session.query(AssistantFileLink).filter(
        AssistantFileLink.file_id == file_id
    ).count() == 0
    assert db_session.query(ProjectMemory).filter(
        ProjectMemory.project_id == project["id"]
    ).count() == 0

    owner_files = client.get("/files", headers=owner_headers)
    assert owner_files.status_code == 200
    assert file_id in {item["id"] for item in owner_files.json()}
    owner_download = client.get(f"/files/{file_id}", headers=owner_headers)
    assert owner_download.status_code == 200
    assert owner_download.content == payload

    workspace_files = client.get(
        "/files",
        params={"workspace_id": workspace["id"]},
        headers=member_headers,
    )
    assert workspace_files.status_code == 200
    assert file_id not in {item["id"] for item in workspace_files.json()}
    member_download = client.get(f"/files/{file_id}", headers=member_headers)
    assert member_download.status_code == 404

    async def unexpected_embedding_call(_query):
        raise AssertionError("Private orphaned project files must not enter workspace RAG.")

    monkeypatch.setattr(rag, "embed_query", unexpected_embedding_call)
    rows = asyncio.run(
        rag.retrieve_relevant_chunks(
            db_session,
            member.id,
            member_conversation_id,
            "confidential project knowledge",
            workspace_id=workspace["id"],
        )
    )
    assert rows == []


def test_account_delete_keeps_other_members_project_uploads_private(
    client, db_session, monkeypatch
):
    from app.config import settings as app_settings
    from app.models.assistant_file_link import AssistantFileLink
    from app.models.assistant_version import AssistantVersion
    from app.models.assistant_workspace_share import AssistantWorkspaceShare
    from app.models.audit_log import AuditLog
    from app.models.file_attachment import FileAttachment
    from app.models.user import User
    from app.models.workspace import WorkspaceMember, WorkspaceRole

    for setting_name in (
        "S3_BUCKET",
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setattr(app_settings, setting_name, "")

    owner_token = _register_and_login(client, "cascade-retention-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _create_workspace(client, owner_headers, "Cascade retention")
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Owned project"},
        headers=owner_headers,
    ).json()

    member_token = _register_and_login(client, "cascade-retention-member@example.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}
    owner = db_session.query(User).filter(
        User.email == "cascade-retention-owner@example.com"
    ).one()
    member = db_session.query(User).filter(
        User.email == "cascade-retention-member@example.com"
    ).one()
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace["id"],
            user_id=member.id,
            role=WorkspaceRole.member,
        )
    )
    assistant = _create_assistant(
        client,
        member_headers,
        name="Member's private assistant",
    )
    attachment = FileAttachment(
        user_id=member.id,
        workspace_id=workspace["id"],
        project_id=project["id"],
        original_filename="member-upload.txt",
        stored_filename="member-upload-cascade.txt",
        object_key=f"users/{member.id}/member-upload-cascade.txt",
        content_type="text/plain",
        size_bytes=12,
        extracted_text="member private",
    )
    db_session.add(attachment)
    db_session.flush()
    db_session.add(
        AssistantFileLink(
            assistant_id=assistant["id"],
            file_id=attachment.id,
        )
    )
    db_session.add(
        AssistantWorkspaceShare(
            assistant_id=assistant["id"],
            workspace_id=workspace["id"],
            shared_by_user_id=member.id,
        )
    )
    historical_version = db_session.query(AssistantVersion).filter(
        AssistantVersion.assistant_id == assistant["id"],
        AssistantVersion.version == 1,
    ).one()
    historical_version.knowledge_file_ids = [attachment.id]
    audit_entry = AuditLog(
        user_id=member.id,
        workspace_id=workspace["id"],
        event_type="test_workspace_retention",
        description="Audit history should survive workspace deletion",
    )
    db_session.add(audit_entry)
    db_session.commit()
    file_id = attachment.id
    audit_entry_id = audit_entry.id

    deleted = client.request(
        "DELETE",
        "/users/me",
        json={"password": "StrongPass123"},
        headers=owner_headers,
    )
    assert deleted.status_code == 204
    db_session.expire_all()

    retained = db_session.get(FileAttachment, file_id)
    assert retained is not None
    assert retained.user_id == member.id
    assert retained.workspace_id is None
    assert retained.project_id is None
    retained_audit_entry = db_session.get(AuditLog, audit_entry_id)
    assert retained_audit_entry is not None
    assert retained_audit_entry.workspace_id is None
    assert db_session.query(AssistantFileLink).filter(
        AssistantFileLink.file_id == file_id
    ).count() == 0
    snapshot = db_session.query(AssistantVersion).filter(
        AssistantVersion.assistant_id == assistant["id"],
        AssistantVersion.version == 1,
    ).one()
    assert snapshot.knowledge_file_ids == []


def test_account_retention_locks_workspaces_containing_owned_projects(
    client, db_session, monkeypatch
):
    """Projects owned by the deleting user can live in another user's workspace."""
    from app.models.file_attachment import FileAttachment
    from app.models.project import WorkspaceProject
    from app.models.user import User
    from app.models.workspace import WorkspaceMember, WorkspaceRole
    from app.services import project_file_retention

    owner_token = _register_and_login(client, "external-workspace-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    workspace = _create_workspace(client, owner_headers, "External project workspace")
    workspace_owner = db_session.query(User).filter_by(
        email="external-workspace-owner@example.com"
    ).one()

    project_owner_token = _register_and_login(
        client, "external-workspace-project-owner@example.com"
    )
    project_owner_headers = {"Authorization": f"Bearer {project_owner_token}"}
    project_owner = db_session.query(User).filter_by(
        email="external-workspace-project-owner@example.com"
    ).one()
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace["id"],
            user_id=project_owner.id,
            role=WorkspaceRole.admin,
        )
    )
    db_session.commit()

    project_response = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Member-owned project"},
        headers=project_owner_headers,
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    attachment = FileAttachment(
        user_id=workspace_owner.id,
        workspace_id=workspace["id"],
        project_id=project_id,
        original_filename="other-uploader.txt",
        stored_filename="other-uploader-retention.txt",
        object_key=f"users/{workspace_owner.id}/other-uploader-retention.txt",
        content_type="text/plain",
        size_bytes=18,
        extracted_text="retained privately",
    )
    db_session.add(attachment)
    db_session.commit()
    file_id = attachment.id

    lock_order = []
    original_user_lock = project_file_retention.lock_user_for_update
    original_workspace_lock = project_file_retention.lock_workspaces_for_update

    def capture_user_lock(db, user_id):
        lock_order.append(("user", user_id))
        return original_user_lock(db, user_id)

    def capture_workspace_lock(db, workspace_ids):
        lock_order.append(("workspace", list(workspace_ids)))
        return original_workspace_lock(db, workspace_ids)

    monkeypatch.setattr(
        project_file_retention, "lock_user_for_update", capture_user_lock
    )
    monkeypatch.setattr(
        project_file_retention, "lock_workspaces_for_update", capture_workspace_lock
    )
    project_file_retention.privatize_account_workspace_attachments(
        db_session, project_owner.id
    )
    db_session.flush()
    db_session.expire_all()

    retained = db_session.get(FileAttachment, file_id)
    assert lock_order[0] == ("user", project_owner.id)
    assert any(
        item[0] == "workspace" and workspace["id"] in item[1]
        for item in lock_order[1:]
    )
    assert retained is not None
    assert retained.user_id == workspace_owner.id
    assert retained.workspace_id is None
    assert retained.project_id is None


def test_project_creation_acquires_workspace_retention_lock(
    client, monkeypatch
):
    from app.routers import projects as projects_router_module

    token = _register_and_login(client, "project-create-lock@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers, "Project creation lock")

    lock_order = []
    original_user_lock = projects_router_module.lock_user_for_update
    original_workspace_lock = projects_router_module.lock_workspaces_for_update

    def capture_user_lock(db, user_id):
        lock_order.append(("user", user_id))
        return original_user_lock(db, user_id)

    def capture_workspace_lock(db, workspace_ids):
        lock_order.append(("workspace", list(workspace_ids)))
        return original_workspace_lock(db, workspace_ids)

    monkeypatch.setattr(
        projects_router_module, "lock_user_for_update", capture_user_lock
    )
    monkeypatch.setattr(
        projects_router_module, "lock_workspaces_for_update", capture_workspace_lock
    )
    created = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Serialized project"},
        headers=headers,
    )

    assert created.status_code == 201
    assert len(lock_order) == 2
    assert lock_order[0][0] == "user"
    assert lock_order[1] == ("workspace", [workspace["id"]])


def test_project_deletion_acquires_workspace_lock_before_conversation_detach(
    client, monkeypatch
):
    from app.routers import projects as projects_router_module

    token = _register_and_login(client, "project-delete-lock@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    workspace = _create_workspace(client, headers, "Project deletion lock")
    project = client.post(
        "/projects",
        json={"workspace_id": workspace["id"], "name": "Lock order project"},
        headers=headers,
    ).json()

    locked = []
    original_lock = projects_router_module.lock_workspaces_for_update

    def capture_lock(db, workspace_ids):
        locked.extend(workspace_ids)
        return original_lock(db, workspace_ids)

    monkeypatch.setattr(
        projects_router_module, "lock_workspaces_for_update", capture_lock
    )
    deleted = client.delete(f"/projects/{project['id']}", headers=headers)

    assert deleted.status_code == 204
    assert locked == [workspace["id"]]


def test_account_deletion_user_lock_serializes_project_creation_on_postgres(
    db_session,
):
    """A project creator must wait while account retention owns the user row."""
    from threading import Event, Thread
    from time import monotonic, sleep
    from uuid import uuid4

    import pytest
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from app.models.user import User
    from app.services.project_file_retention import lock_user_for_update

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this regression test")

    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    email = f"retention-lock-{uuid4().hex}@example.test"
    creator = session_factory()
    user = User(email=email, hashed_password="test-only-hash")
    creator.add(user)
    creator.commit()
    user_id = user.id
    creator.close()

    retention = session_factory()
    contender_started = Event()
    contender_acquired = Event()
    contender_pid = {}

    def attempt_project_owner_lock():
        with session_factory() as contender:
            contender.begin()
            contender_pid["value"] = contender.execute(
                text("SELECT pg_backend_pid()")
            ).scalar_one()
            contender_started.set()
            lock_user_for_update(contender, user_id)
            contender_acquired.set()
            contender.rollback()

    thread = Thread(target=attempt_project_owner_lock, daemon=True)
    try:
        retention.begin()
        lock_user_for_update(retention, user_id)
        thread.start()
        assert contender_started.wait(5), "contender did not start"

        deadline = monotonic() + 5
        waiting_on_lock = False
        while monotonic() < deadline:
            with session_factory() as probe:
                wait_type = probe.execute(
                    text(
                        "SELECT wait_event_type FROM pg_stat_activity "
                        "WHERE pid = :pid"
                    ),
                    {"pid": contender_pid["value"]},
                ).scalar_one_or_none()
            if wait_type == "Lock":
                waiting_on_lock = True
                break
            sleep(0.01)

        assert waiting_on_lock, "project-creation lock did not wait on the user row"
        assert not contender_acquired.is_set()
        retention.commit()
        assert contender_acquired.wait(5), "contender did not acquire the released user lock"
        thread.join(timeout=5)
        assert not thread.is_alive()
    finally:
        if retention.in_transaction():
            retention.rollback()
        if thread.ident is not None:
            thread.join(timeout=5)
        retention.close()
        with session_factory() as cleanup:
            cleanup.query(User).filter(User.id == user_id).delete()
            cleanup.commit()
