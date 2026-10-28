"""
اختبارات المرحلة السادسة: رفع الملفات وإدارتها
"""
import zipfile

import pytest
from fastapi import HTTPException

from app.config import settings as app_settings


def _register_and_login(client, email="files@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def _disable_object_storage(monkeypatch):
    """Keep route tests deterministic and independent of any real S3 endpoint."""
    for name in (
        "S3_BUCKET",
        "S3_ENDPOINT_URL",
        "S3_REGION",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setattr(app_settings, name, "")



def _mark_file_as_indexed(attachment):
    from datetime import datetime, timezone
    from app.models.file_attachment import extracted_text_fingerprint
    from app.services.embeddings import get_embedding_index_identity

    provider, model, fingerprint = get_embedding_index_identity()
    text_fingerprint = extracted_text_fingerprint(attachment.extracted_text)
    attachment.extracted_text_sha256 = text_fingerprint
    attachment.indexed_text_sha256 = text_fingerprint
    attachment.indexed_embedding_fingerprint = fingerprint
    attachment.indexed_embedding_provider = provider
    attachment.indexed_embedding_model = model
    attachment.indexed_at = datetime.now(timezone.utc)


def test_upload_file_success(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/files/upload", files={"file": ("test.png", b"\x89PNG\r\n\x1a\n" + b"fake", "image/png")}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "test.png"
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] == len(b"\x89PNG\r\n\x1a\n" + b"fake")


def test_upload_rejects_unsupported_type(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    response = client.post("/files/upload", files={"file": ("virus.exe", b"binary", "application/x-msdownload")}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 415
    detail = response.json()["detail"]
    assert "DOCX" in detail
    assert "XLSX" in detail
    assert "CSV" in detail
    assert "TXT" in detail


def test_upload_rejects_oversized_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(app_settings, "MAX_UPLOAD_SIZE_MB", 0)
    token = _register_and_login(client)
    response = client.post("/files/upload", files={"file": ("small.png", b"\x89PNG\r\n\x1a\n" + b"x", "image/png")}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 413


def test_list_files(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/files/upload", files={"file": ("a.pdf", b"%PDF-1.4 pdf-bytes", "application/pdf")}, headers=headers)
    response = client.get("/files", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_download_file_returns_original_bytes(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    upload_response = client.post("/files/upload", files={"file": ("note.csv", b"a,b,c\n1,2,3", "text/csv")}, headers=headers)
    file_id = upload_response.json()["id"]
    download_response = client.get(f"/files/{file_id}", headers=headers)
    assert download_response.status_code == 200
    assert download_response.content == b"a,b,c\n1,2,3"


def test_download_file_safely_encodes_untrusted_filename(
    client, db_session, tmp_path, monkeypatch
):
    """Control characters and separators must not alter download headers."""
    from app.models.file_attachment import FileAttachment
    from app.routers import files as files_router

    monkeypatch.setattr(files_router, "index_file_chunks", lambda _db, _file: 0)

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client, "filename-header@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    upload_response = client.post(
        "/files/upload",
        files={"file": ("normal.txt", b"safe text", "text/plain")},
        headers=headers,
    )
    assert upload_response.status_code == 201

    attachment = db_session.get(FileAttachment, upload_response.json()["id"])
    assert attachment is not None
    attachment.original_filename = 'report";\r\nX-Injected: yes - résumé.txt'
    db_session.commit()

    response = client.get(f"/files/{attachment.id}", headers=headers)

    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert "\r" not in disposition
    assert "\n" not in disposition
    assert disposition.startswith('attachment; filename="')
    assert "filename*=UTF-8''" in disposition
    assert "%22%3B" in disposition
    assert "%C3%A9" in disposition
    assert response.content == b"safe text"


def test_file_audit_description_sanitizes_untrusted_filename(
    client, db_session, tmp_path, monkeypatch
):
    """A malicious filename must not create additional audit-log lines."""
    from app.models.audit_log import AuditLog
    from app.models.file_attachment import FileAttachment
    from app.routers import files as files_router

    monkeypatch.setattr(files_router, "index_file_chunks", lambda _db, _file: 0)

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client, "filename-audit@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    uploaded = client.post(
        "/files/upload",
        files={"file": ("normal.txt", b"safe text", "text/plain")},
        headers=headers,
    )
    assert uploaded.status_code == 201

    attachment = db_session.get(FileAttachment, uploaded.json()["id"])
    assert attachment is not None
    file_id = attachment.id
    owner_id = attachment.user_id
    attachment.original_filename = "notes.txt\r\n[INFO] forged audit entry"
    db_session.commit()

    deleted = client.delete(f"/files/{file_id}", headers=headers)
    assert deleted.status_code == 204

    db_session.expire_all()
    entry = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.user_id == owner_id,
            AuditLog.event_type == "file_deleted",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert entry is not None
    assert "\r" not in entry.description
    assert "\n" not in entry.description
    assert "[INFO]" not in entry.description
    assert "(INFO) forged audit entry" in entry.description


def test_delete_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    upload_response = client.post("/files/upload", files={"file": ("a.png", b"\x89PNG\r\n\x1a\n" + b"bytes", "image/png")}, headers=headers)
    file_id = upload_response.json()["id"]
    delete_response = client.delete(f"/files/{file_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/files/{file_id}", headers=headers).status_code == 404



def test_deleting_file_cascades_to_rag_chunks(
    client, db_session, tmp_path, monkeypatch
):
    """A deleted upload must not leave stale retrievable chunks behind."""
    from app.models.file_chunk import FileChunk
    from app.routers import files as files_router

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))

    def fake_index_file_chunks(db, attachment):
        db.add(
            FileChunk(
                file_id=attachment.id,
                chunk_index=0,
                content="This text should be removed with its source file.",
                embedding=None,
            )
        )
        db.flush()
        return 1

    monkeypatch.setattr(files_router, "index_file_chunks", fake_index_file_chunks)
    token = _register_and_login(client, "rag-delete-cascade@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    uploaded = client.post(
        "/files/upload",
        files={"file": ("knowledge.txt", b"Knowledge to index.", "text/plain")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]
    assert (
        db_session.query(FileChunk)
        .filter(FileChunk.file_id == file_id)
        .count()
        == 1
    )

    deleted = client.delete(f"/files/{file_id}", headers=headers)

    assert deleted.status_code == 204
    assert (
        db_session.query(FileChunk)
        .filter(FileChunk.file_id == file_id)
        .count()
        == 0
    )


def test_deleting_file_removes_assistant_knowledge_link_and_chunks(
    client, db_session, tmp_path, monkeypatch
):
    """Deleting a personal upload must also detach it from assistant knowledge."""
    from app.models.assistant import Assistant
    from app.models.assistant_file_link import AssistantFileLink
    from app.models.file_chunk import FileChunk
    from app.models.user import User
    from app.routers import files as files_router

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    _disable_object_storage(monkeypatch)

    def fake_index_file_chunks(db, attachment):
        db.add(
            FileChunk(
                file_id=attachment.id,
                chunk_index=0,
                content="Assistant knowledge to remove with the source file.",
                embedding=None,
            )
        )
        db.flush()
        return 1

    monkeypatch.setattr(files_router, "index_file_chunks", fake_index_file_chunks)
    token = _register_and_login(client, "assistant-file-delete-cascade@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    uploaded = client.post(
        "/files/upload",
        files={
            "file": (
                "assistant-notes.txt",
                b"Assistant knowledge to remove with the source file.",
                "text/plain",
            )
        },
        headers=headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]

    owner = db_session.query(User).filter_by(
        email="assistant-file-delete-cascade@example.com"
    ).one()
    assistant = Assistant(
        user_id=owner.id,
        name="Delete cascade test assistant",
        instructions="Use the linked knowledge when it is available.",
    )
    db_session.add(assistant)
    db_session.flush()
    db_session.add(AssistantFileLink(assistant_id=assistant.id, file_id=file_id))
    db_session.commit()

    deleted = client.delete(f"/files/{file_id}", headers=headers)
    assert deleted.status_code == 204

    db_session.expire_all()
    assert db_session.get(Assistant, assistant.id) is not None
    assert (
        db_session.query(AssistantFileLink)
        .filter(AssistantFileLink.file_id == file_id)
        .count()
        == 0
    )
    assert (
        db_session.query(FileChunk)
        .filter(FileChunk.file_id == file_id)
        .count()
        == 0
    )


def test_reindex_file_retries_saved_text_after_embedding_provider_failure(
    client, db_session, tmp_path, monkeypatch
):
    """A failed index remains retryable without uploading the source again."""
    from app.models.file_attachment import FileAttachment
    from app.models.file_chunk import FileChunk
    from app.routers import files as files_router
    from app.services.embeddings import EmbeddingServiceError

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    _disable_object_storage(monkeypatch)
    monkeypatch.setattr(
        files_router, "enforce_daily_ai_limit", lambda current_user, _db: current_user
    )
    monkeypatch.setattr(
        files_router,
        "enforce_workspace_daily_ai_limit",
        lambda _workspace_id, _current_user, _db: None,
    )

    attempts = 0

    def fail_twice_then_index(db, attachment):
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise EmbeddingServiceError("simulated embedding outage")
        db.add(
            FileChunk(
                file_id=attachment.id,
                chunk_index=0,
                content="Linux network notes for retry testing.",
                embedding=[0.1] * 768,
            )
        )
        _mark_file_as_indexed(attachment)
        db.flush()
        return 1

    monkeypatch.setattr(files_router, "index_file_chunks", fail_twice_then_index)
    token = _register_and_login(client, "files-reindex-retry@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    payload = b"Linux network notes for retry testing."

    uploaded = client.post(
        "/files/upload",
        files={"file": ("network-notes.txt", payload, "text/plain")},
        headers=headers,
    )

    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]
    assert uploaded.json()["has_extracted_text"] is True
    assert uploaded.json()["is_ai_indexed"] is False
    assert attempts == 1

    failed_retry = client.post(f"/files/{file_id}/reindex", headers=headers)
    assert failed_retry.status_code == 503
    assert "simulated embedding outage" not in failed_retry.text
    assert attempts == 2

    db_session.expire_all()
    persisted = db_session.get(FileAttachment, file_id)
    assert persisted is not None
    assert persisted.extracted_text
    assert (
        db_session.query(FileChunk)
        .filter(
            FileChunk.file_id == file_id,
            FileChunk.embedding.is_not(None),
        )
        .count()
        == 0
    )

    retried = client.post(f"/files/{file_id}/reindex", headers=headers)

    assert retried.status_code == 200
    assert retried.json()["has_extracted_text"] is True
    assert retried.json()["is_ai_indexed"] is True
    assert attempts == 3
    assert (
        db_session.query(FileChunk)
        .filter(
            FileChunk.file_id == file_id,
            FileChunk.embedding.is_not(None),
        )
        .count()
        == 1
    )


def test_reindex_file_rejects_upload_without_extracted_text(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    _disable_object_storage(monkeypatch)
    token = _register_and_login(client, "files-reindex-no-text@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    uploaded = client.post(
        "/files/upload",
        files={
            "file": (
                "chart.png",
                b"\x89PNG\r\n\x1a\nmock-image",
                "image/png",
            )
        },
        headers=headers,
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["has_extracted_text"] is False

    response = client.post(
        f"/files/{uploaded.json()['id']}/reindex",
        headers=headers,
    )

    assert response.status_code == 422


def test_cannot_access_other_users_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token_a = _register_and_login(client, "filesowner@example.com")
    upload_response = client.post("/files/upload", files={"file": ("secret.pdf", b"%PDF-1.4 bytes", "application/pdf")}, headers={"Authorization": f"Bearer {token_a}"})
    file_id = upload_response.json()["id"]
    token_b = _register_and_login(client, "filesintruder@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    assert client.get(f"/files/{file_id}", headers=headers_b).status_code == 404
    assert client.delete(f"/files/{file_id}", headers=headers_b).status_code == 404
    assert client.post(f"/files/{file_id}/reindex", headers=headers_b).status_code == 404


def test_files_require_authentication(client):
    assert client.get("/files").status_code == 401
    assert client.post("/files/upload", files={"file": ("a.png", b"x", "image/png")}).status_code == 401


def test_workspace_file_is_shared_with_members_but_personal_files_are_not(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))

    token_owner = _register_and_login(client, "workspace-file-owner@example.com")
    from app.models.user import User
    owner = db_session.query(User).filter_by(email="workspace-file-owner@example.com").one()
    workspace = owner.owned_workspaces[0]
    owner_headers = {"Authorization": f"Bearer {token_owner}"}

    upload_response = client.post(
        "/files/upload",
        params={"workspace_id": workspace.id},
        files={"file": ("shared.txt", b"shared knowledge", "text/plain")},
        headers=owner_headers,
    )
    assert upload_response.status_code == 201
    shared_id = upload_response.json()["id"]
    assert upload_response.json()["workspace_id"] == workspace.id
    assert upload_response.json()["is_owner"] is True

    token_member = _register_and_login(client, "workspace-file-member@example.com")
    member = db_session.query(User).filter_by(email="workspace-file-member@example.com").one()
    from app.models.workspace import WorkspaceMember, WorkspaceRole
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=member.id,
            role=WorkspaceRole.member,
        )
    )
    db_session.commit()
    member_headers = {"Authorization": f"Bearer {token_member}"}

    listed = client.get(
        "/files",
        params={"workspace_id": workspace.id},
        headers=member_headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == shared_id
    assert listed.json()[0]["is_owner"] is False
    assert listed.json()[0]["can_delete"] is False

    downloaded = client.get(f"/files/{shared_id}", headers=member_headers)
    assert downloaded.status_code == 200
    assert downloaded.content == b"shared knowledge"

    assert client.delete(f"/files/{shared_id}", headers=member_headers).status_code == 403

    personal = client.post(
        "/files/upload",
        files={"file": ("private.txt", b"private", "text/plain")},
        headers=owner_headers,
    )
    private_id = personal.json()["id"]

    assert client.get(f"/files/{private_id}", headers=member_headers).status_code == 404
    assert client.delete(f"/files/{private_id}", headers=member_headers).status_code == 404


def test_workspace_file_requires_workspace_membership(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token_owner = _register_and_login(client, "workspace-scope-owner@example.com")
    from app.models.user import User
    owner = db_session.query(User).filter_by(email="workspace-scope-owner@example.com").one()
    workspace = owner.owned_workspaces[0]

    token_other = _register_and_login(client, "workspace-scope-other@example.com")
    headers = {"Authorization": f"Bearer {token_other}"}

    response = client.get(
        "/files",
        params={"workspace_id": workspace.id},
        headers=headers,
    )
    assert response.status_code == 404


def test_upload_file_to_project_and_list(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))

    token = _register_and_login(client, "project-file-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    from app.models.user import User

    owner = db_session.query(User).filter_by(email="project-file-owner@example.com").one()
    workspace = owner.owned_workspaces[0]

    project = client.post(
        "/projects",
        json={"workspace_id": workspace.id, "name": "Research"},
        headers=headers,
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    uploaded = client.post(
        "/files/upload",
        params={"project_id": project_id},
        files={"file": ("knowledge.txt", b"project knowledge", "text/plain")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["project_id"] == project_id
    assert uploaded.json()["workspace_id"] == workspace.id

    listed = client.get(
        "/files",
        params={"project_id": project_id},
        headers=headers,
    )
    assert listed.status_code == 200
    assert [item["project_id"] for item in listed.json()] == [project_id]


def test_project_file_requires_project_membership(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))

    token_owner = _register_and_login(client, "project-file-scope-owner@example.com")
    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    from app.models.user import User

    owner = db_session.query(User).filter_by(email="project-file-scope-owner@example.com").one()
    workspace = owner.owned_workspaces[0]
    project_id = client.post(
        "/projects",
        json={"workspace_id": workspace.id, "name": "Private Knowledge"},
        headers=headers_owner,
    ).json()["id"]

    uploaded = client.post(
        "/files/upload",
        params={"project_id": project_id},
        files={"file": ("secret.txt", b"private project knowledge", "text/plain")},
        headers=headers_owner,
    )
    assert uploaded.status_code == 201

    token_other = _register_and_login(client, "project-file-scope-other@example.com")
    response = client.get(
        "/files",
        params={"project_id": project_id},
        headers={"Authorization": f"Bearer {token_other}"},
    )
    assert response.status_code == 404


def test_project_file_cannot_attach_to_different_project_conversation(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    from app.models.user import User
    from app.models.conversation_file_link import ConversationFileLink
    from app.routers import chat as chat_router_module
    from app.services.ai_providers.base import AIReply
    from unittest.mock import AsyncMock

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )

    token = _register_and_login(client, "project-file-mismatch@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    owner = db_session.query(User).filter_by(email="project-file-mismatch@example.com").one()
    workspace = owner.owned_workspaces[0]

    project_a = client.post(
        "/projects",
        json={"workspace_id": workspace.id, "name": "A"},
        headers=headers,
    ).json()["id"]
    project_b = client.post(
        "/projects",
        json={"workspace_id": workspace.id, "name": "B"},
        headers=headers,
    ).json()["id"]

    conversation_id = client.post(
        "/chat",
        json={"message": "ابدأ", "workspace_id": workspace.id, "project_id": project_a},
        headers=headers,
    ).json()["conversation_id"]

    uploaded = client.post(
        "/files/upload",
        params={"project_id": project_b},
        files={"file": ("other.txt", b"other", "text/plain")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]

    attached = client.post(
        f"/files/{file_id}/attach/{conversation_id}",
        headers=headers,
    )
    assert attached.status_code == 400

    # Simulate a stale/legacy cross-project link. Detaching must apply the same
    # project-scope policy as attaching and must leave the link untouched.
    db_session.add(
        ConversationFileLink(
            conversation_id=conversation_id,
            file_id=file_id,
        )
    )
    db_session.commit()

    detached = client.delete(
        f"/files/{file_id}/attach/{conversation_id}",
        headers=headers,
    )
    assert detached.status_code == 400
    assert (
        db_session.query(ConversationFileLink)
        .filter(
            ConversationFileLink.conversation_id == conversation_id,
            ConversationFileLink.file_id == file_id,
        )
        .first()
        is not None
    )




def test_object_storage_upload_download_delete_survives_local_file_loss(
    client, db_session, tmp_path, monkeypatch
):
    """Exercise the file API against a remote-object-store stand-in."""
    import io

    from app.models.file_attachment import FileAttachment
    from app.routers import files as files_router

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    for name, value in (
        ("S3_BUCKET", "test-bucket"),
        ("S3_ENDPOINT_URL", "https://objects.example.test"),
        ("S3_REGION", "us-east-1"),
        ("S3_ACCESS_KEY_ID", "test-access-key"),
        ("S3_SECRET_ACCESS_KEY", "test-secret-key"),
    ):
        monkeypatch.setattr(app_settings, name, value)

    objects = {}
    operations = []

    def fake_put_file(path, object_key, content_type):
        objects[object_key] = path.read_bytes()
        operations.append(("put", object_key, content_type))

    def fake_open_file(object_key, fallback_path):
        operations.append(("get", object_key))
        try:
            return io.BytesIO(objects[object_key])
        except KeyError as exc:
            raise FileNotFoundError(object_key) from exc

    def fake_delete_file(object_key, fallback_path):
        operations.append(("delete", object_key))
        objects.pop(object_key, None)
        fallback_path.unlink(missing_ok=True)

    monkeypatch.setattr(files_router, "put_file", fake_put_file)
    monkeypatch.setattr(files_router, "open_file", fake_open_file)
    monkeypatch.setattr(files_router, "delete_stored_file", fake_delete_file)
    monkeypatch.setattr(files_router, "index_file_chunks", lambda db, file: 0)

    token = _register_and_login(client, "remote-storage-roundtrip@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    original_bytes = b"Durable object storage content.\nSecond line."

    uploaded = client.post(
        "/files/upload",
        files={"file": ("durable.txt", original_bytes, "text/plain")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]
    attachment = db_session.get(FileAttachment, file_id)
    assert attachment is not None
    object_key = attachment.object_key
    assert object_key in objects
    assert objects[object_key] == original_bytes
    assert attachment.extracted_text == original_bytes.decode("utf-8")

    # Simulate a Render redeploy: the ephemeral local copy is no longer available.
    local_path = tmp_path / str(attachment.user_id) / attachment.stored_filename
    local_path.unlink()

    downloaded = client.get(f"/files/{file_id}", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == original_bytes

    deleted = client.delete(f"/files/{file_id}", headers=headers)
    assert deleted.status_code == 204
    assert object_key not in objects
    assert client.get(f"/files/{file_id}", headers=headers).status_code == 404
    assert [operation[0] for operation in operations] == ["put", "get", "delete"]


def test_upload_failure_cleans_partial_file_and_allows_retry(
    client, db_session, tmp_path, monkeypatch
):
    """A remote storage outage cleans up the upload; a retry persists the original bytes."""
    import io

    from app.models.file_attachment import FileAttachment
    from app.models.user import User
    from app.routers import files as files_router
    from app.services.storage import StorageError

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    for name, value in (
        ("S3_BUCKET", "test-bucket"),
        ("S3_ENDPOINT_URL", "https://objects.example.test"),
        ("S3_REGION", "us-east-1"),
        ("S3_ACCESS_KEY_ID", "test-access-key"),
        ("S3_SECRET_ACCESS_KEY", "test-secret-key"),
    ):
        monkeypatch.setattr(app_settings, name, value)

    payload = b"file content that should survive a successful retry"
    attempts = 0
    objects = {}
    operations = []

    def fake_put_file(path, object_key, content_type):
        nonlocal attempts
        attempts += 1
        assert path.read_bytes() == payload
        assert object_key.startswith("users/")
        assert content_type == "text/plain"
        if attempts == 1:
            operations.append(("put_failed", object_key))
            raise StorageError("simulated temporary object-storage outage")
        objects[object_key] = path.read_bytes()
        operations.append(("put", object_key, content_type))

    def fake_open_file(object_key, fallback_path):
        operations.append(("get", object_key))
        try:
            return io.BytesIO(objects[object_key])
        except KeyError as exc:
            raise FileNotFoundError(object_key) from exc

    monkeypatch.setattr(files_router, "put_file", fake_put_file)
    monkeypatch.setattr(files_router, "open_file", fake_open_file)
    monkeypatch.setattr(files_router, "index_file_chunks", lambda db, file: 0)
    token = _register_and_login(client, "files-storage-failure@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    upload = {"file": ("retry-me.txt", payload, "text/plain")}

    failed = client.post("/files/upload", files=upload, headers=headers)

    assert failed.status_code == 503
    assert objects == {}
    user = db_session.query(User).filter_by(
        email="files-storage-failure@example.com"
    ).one()
    assert (
        db_session.query(FileAttachment)
        .filter(FileAttachment.user_id == user.id)
        .count()
        == 0
    )
    assert not any(path.is_file() for path in tmp_path.rglob("*"))

    retried = client.post("/files/upload", files=upload, headers=headers)
    assert retried.status_code == 201
    assert attempts == 2
    file_id = retried.json()["id"]

    attachment = db_session.get(FileAttachment, file_id)
    assert attachment is not None
    assert objects[attachment.object_key] == payload
    assert (
        db_session.query(FileAttachment)
        .filter(FileAttachment.user_id == user.id)
        .count()
        == 1
    )

    # Prove retrieval comes from the remote object store, not the ephemeral disk copy.
    local_path = tmp_path / str(attachment.user_id) / attachment.stored_filename
    local_path.unlink()
    downloaded = client.get(f"/files/{file_id}", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == payload
    assert [operation[0] for operation in operations] == ["put_failed", "put", "get"]


def test_upload_preserves_original_file_when_text_extraction_fails(
    client, db_session, tmp_path, monkeypatch
):
    """Text extraction failure is reported internally but must not destroy the upload."""
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    _disable_object_storage(monkeypatch)
    from app.models.file_attachment import FileAttachment
    from app.routers import files as files_router
    from app.services.file_text_extractor import FileTextExtractionError

    payload = b"valid uploaded content; extraction will fail"

    def fail_extract(*_args, **_kwargs):
        raise FileTextExtractionError("simulated parser failure")

    monkeypatch.setattr(files_router, "extract_text", fail_extract)
    token = _register_and_login(client, "files-extraction-failure@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    uploaded = client.post(
        "/files/upload",
        files={"file": ("notes.txt", payload, "text/plain")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]

    attachment = db_session.get(FileAttachment, file_id)
    assert attachment is not None
    assert attachment.extracted_text is None

    downloaded = client.get(f"/files/{file_id}", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == payload


def test_project_file_access_requires_project_membership_and_edit_role(
    client, db_session, tmp_path, monkeypatch
):
    """Workspace membership alone must not expose private project files."""
    from app.models.project_member import ProjectMember, ProjectMemberRole
    from app.models.user import User
    from app.models.workspace import WorkspaceMember, WorkspaceRole
    from app.routers import files as files_router

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    _disable_object_storage(monkeypatch)
    monkeypatch.setattr(files_router, "index_file_chunks", lambda _db, _file: 0)

    owner_token = _register_and_login(client, "project-file-acl-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner = db_session.query(User).filter_by(
        email="project-file-acl-owner@example.com"
    ).one()
    workspace = owner.owned_workspaces[0]

    project_response = client.post(
        "/projects",
        json={"workspace_id": workspace.id, "name": "Private files"},
        headers=owner_headers,
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    uploaded = client.post(
        "/files/upload",
        params={"project_id": project_id},
        files={"file": ("private.txt", b"Private project contents.", "text/plain")},
        headers=owner_headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]

    outsider_token = _register_and_login(
        client, "project-file-acl-outsider@example.com"
    )
    outsider = db_session.query(User).filter_by(
        email="project-file-acl-outsider@example.com"
    ).one()
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=outsider.id,
            role=WorkspaceRole.member,
        )
    )

    viewer_token = _register_and_login(
        client, "project-file-acl-viewer@example.com"
    )
    viewer = db_session.query(User).filter_by(
        email="project-file-acl-viewer@example.com"
    ).one()
    db_session.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=viewer.id,
            role=WorkspaceRole.member,
        )
    )
    db_session.add(
        ProjectMember(
            project_id=project_id,
            user_id=viewer.id,
            role=ProjectMemberRole.viewer,
        )
    )
    db_session.commit()

    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    assert client.get(
        "/files",
        params={"project_id": project_id},
        headers=outsider_headers,
    ).status_code == 404
    assert client.get(
        f"/files/{file_id}",
        headers=outsider_headers,
    ).status_code == 404
    assert client.post(
        f"/files/{file_id}/reindex",
        headers=outsider_headers,
    ).status_code == 404
    assert client.post(
        "/files/upload",
        params={"project_id": project_id},
        files={"file": ("intruder.txt", b"not allowed", "text/plain")},
        headers=outsider_headers,
    ).status_code == 404

    workspace_listing = client.get(
        "/files",
        params={"workspace_id": workspace.id},
        headers=outsider_headers,
    )
    assert workspace_listing.status_code == 200
    assert file_id not in {file["id"] for file in workspace_listing.json()}

    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    project_listing = client.get(
        "/files",
        params={"project_id": project_id},
        headers=viewer_headers,
    )
    assert project_listing.status_code == 200
    assert [file["id"] for file in project_listing.json()] == [file_id]

    mismatch_listing = client.get(
        "/files",
        params={"project_id": project_id, "workspace_id": workspace.id + 9999},
        headers=viewer_headers,
    )
    assert mismatch_listing.status_code == 400
    assert project_listing.json()[0]["can_delete"] is False
    assert client.get(f"/files/{file_id}", headers=viewer_headers).status_code == 200
    assert client.post(
        f"/files/{file_id}/reindex",
        headers=viewer_headers,
    ).status_code == 403
    assert client.post(
        f"/files/{file_id}/index-image",
        headers=viewer_headers,
    ).status_code == 403

    denied_upload = client.post(
        "/files/upload",
        params={"project_id": project_id},
        files={"file": ("viewer-upload.txt", b"viewers cannot upload", "text/plain")},
        headers=viewer_headers,
    )
    assert denied_upload.status_code == 403


def test_upload_preserves_extracted_text_when_ai_limit_defers_indexing(
    client, db_session, tmp_path, monkeypatch
):
    """Quota rejection skips embeddings but must not discard a successful upload."""
    from fastapi import HTTPException

    from app.models.file_attachment import FileAttachment
    from app.routers import files as files_router

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    _disable_object_storage(monkeypatch)
    token = _register_and_login(client, "files-ai-limit-deferred@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    def reject_indexing(_current_user, _db):
        raise HTTPException(status_code=429, detail="synthetic rate-limit test")

    index_calls = []

    def should_not_index(_db, _file):
        index_calls.append(True)
        raise AssertionError("Embedding provider must not be called after quota rejection")

    monkeypatch.setattr(files_router, "enforce_daily_ai_limit", reject_indexing)
    monkeypatch.setattr(files_router, "index_file_chunks", should_not_index)

    payload = b"Extracted notes should survive a deferred embedding attempt."
    response = client.post(
        "/files/upload",
        files={"file": ("quota-deferred.txt", payload, "text/plain")},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["has_extracted_text"] is True
    assert response.json()["is_ai_indexed"] is False
    assert index_calls == []

    db_session.expire_all()
    stored = db_session.get(FileAttachment, response.json()["id"])
    assert stored is not None
    assert stored.extracted_text == payload.decode("utf-8")


def test_file_is_reported_unindexed_when_embedding_configuration_changes(
    client, tmp_path, monkeypatch
):
    from app.models.file_chunk import FileChunk
    from app.routers import files as files_router

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    _disable_object_storage(monkeypatch)

    def fake_index_file_chunks(db, attachment):
        db.add(
            FileChunk(
                file_id=attachment.id,
                chunk_index=0,
                content=attachment.extracted_text or "",
                embedding=[0.1] * 768,
            )
        )
        _mark_file_as_indexed(attachment)
        db.flush()
        return 1

    monkeypatch.setattr(files_router, "index_file_chunks", fake_index_file_chunks)
    token = _register_and_login(client, "stale-index-status@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    uploaded = client.post(
        "/files/upload",
        files={
            "file": (
                "indexed-notes.txt",
                b"These notes were indexed using the current embedding configuration.",
                "text/plain",
            )
        },
        headers=headers,
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["is_ai_indexed"] is True

    previous_identity = files_router.get_embedding_index_identity()
    monkeypatch.setattr(
        files_router,
        "get_embedding_index_identity",
        lambda: (
            previous_identity[0],
            previous_identity[1],
            f"stale-{previous_identity[2]}",
        ),
    )
    listed = client.get("/files", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["is_ai_indexed"] is False


def test_file_status_tracks_source_change_and_reindex_cycle(
    client, db_session, tmp_path, monkeypatch
):
    """File status must turn stale after source edits and recover after reindexing."""
    from app.models.file_attachment import FileAttachment
    from app.models.file_chunk import FileChunk
    from app.routers import files as files_router

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    _disable_object_storage(monkeypatch)
    monkeypatch.setattr(
        files_router,
        "enforce_daily_ai_limit",
        lambda current_user, _db: current_user,
    )

    index_attempts = 0

    def fake_index_file_chunks(db, attachment):
        nonlocal index_attempts
        index_attempts += 1
        db.query(FileChunk).filter(
            FileChunk.file_id == attachment.id
        ).delete(synchronize_session=False)
        text = (attachment.extracted_text or "").strip()
        if not text:
            return 0
        db.add(
            FileChunk(
                file_id=attachment.id,
                chunk_index=0,
                content=text,
                embedding=[0.1] * 768,
            )
        )
        _mark_file_as_indexed(attachment)
        db.flush()
        return 1

    monkeypatch.setattr(files_router, "index_file_chunks", fake_index_file_chunks)
    token = _register_and_login(client, "files-stale-source-reindex@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    uploaded = client.post(
        "/files/upload",
        files={
            "file": (
                "source-notes.txt",
                b"Original source text that has been indexed.",
                "text/plain",
            )
        },
        headers=headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]
    assert uploaded.json()["is_ai_indexed"] is True
    assert index_attempts == 1

    attachment = db_session.get(FileAttachment, file_id)
    assert attachment is not None
    attachment.extracted_text = "Updated source text that requires reindexing."
    db_session.commit()
    db_session.expire_all()

    stale_attachment = db_session.get(FileAttachment, file_id)
    assert stale_attachment is not None
    assert stale_attachment.extracted_text_sha256 != stale_attachment.indexed_text_sha256

    listed = client.get("/files", headers=headers)
    assert listed.status_code == 200
    stale_response = next(item for item in listed.json() if item["id"] == file_id)
    assert stale_response["has_extracted_text"] is True
    assert stale_response["is_ai_indexed"] is False

    retried = client.post(f"/files/{file_id}/reindex", headers=headers)
    assert retried.status_code == 200
    assert retried.json()["is_ai_indexed"] is True
    assert index_attempts == 2

    db_session.expire_all()
    indexed_attachment = db_session.get(FileAttachment, file_id)
    assert indexed_attachment is not None
    assert indexed_attachment.indexed_text_sha256 == indexed_attachment.extracted_text_sha256
    assert (
        db_session.query(FileChunk)
        .filter(FileChunk.file_id == file_id)
        .count()
        == 1
    )
    chunk = db_session.query(FileChunk).filter(FileChunk.file_id == file_id).one()
    assert chunk.content == "Updated source text that requires reindexing."
    assert "Original source text that has been indexed." not in chunk.content


def test_file_operations_recheck_current_project_and_workspace_access(
    client, db_session, tmp_path, monkeypatch
):
    """An owned conversation does not preserve revoked project/workspace access."""
    from app.models.conversation import Conversation
    from app.models.conversation_file_link import ConversationFileLink
    from app.models.file_attachment import FileAttachment
    from app.models.project_member import ProjectMember, ProjectMemberRole
    from app.models.user import User
    from app.models.workspace import WorkspaceMember, WorkspaceRole

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    owner_token = _register_and_login(client, "file-conversation-scope-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    owner = db_session.query(User).filter_by(
        email="file-conversation-scope-owner@example.com"
    ).one()
    workspace = owner.owned_workspaces[0]

    created_project = client.post(
        "/projects",
        json={"workspace_id": workspace.id, "name": "File conversation access"},
        headers=owner_headers,
    )
    assert created_project.status_code == 201
    project_id = created_project.json()["id"]

    member_token = _register_and_login(
        client, "file-conversation-scope-member@example.com"
    )
    member_headers = {"Authorization": f"Bearer {member_token}"}
    member = db_session.query(User).filter_by(
        email="file-conversation-scope-member@example.com"
    ).one()
    workspace_membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=member.id,
        role=WorkspaceRole.member,
    )
    project_membership = ProjectMember(
        project_id=project_id,
        user_id=member.id,
        role=ProjectMemberRole.editor,
    )
    db_session.add_all([workspace_membership, project_membership])
    db_session.flush()

    conversation = Conversation(
        user_id=member.id,
        workspace_id=workspace.id,
        project_id=project_id,
        title="Conversation loses project access",
    )
    file_a = FileAttachment(
        user_id=member.id,
        original_filename="personal-a.txt",
        stored_filename="personal-a.txt",
        content_type="text/plain",
        size_bytes=12,
        extracted_text="Personal attachment A.",
    )
    file_b = FileAttachment(
        user_id=member.id,
        original_filename="personal-b.txt",
        stored_filename="personal-b.txt",
        content_type="text/plain",
        size_bytes=12,
        extracted_text="Personal attachment B.",
    )
    db_session.add_all([conversation, file_a, file_b])
    db_session.flush()
    db_session.add(
        ConversationFileLink(conversation_id=conversation.id, file_id=file_a.id)
    )
    db_session.commit()

    params = {"conversation_id": conversation.id, "include_unattached": "true"}
    assert client.get("/files", params=params, headers=member_headers).status_code == 200
    assert client.post(
        f"/files/{file_b.id}/attach/{conversation.id}",
        headers=member_headers,
    ).status_code == 200

    def assert_conversation_file_operations_denied():
        assert client.get(
            "/files", params=params, headers=member_headers
        ).status_code == 404
        assert client.post(
            f"/files/{file_a.id}/attach/{conversation.id}",
            headers=member_headers,
        ).status_code == 404
        assert client.delete(
            f"/files/{file_a.id}/attach/{conversation.id}",
            headers=member_headers,
        ).status_code == 404

        db_session.expire_all()
        prior_count = (
            db_session.query(FileAttachment)
            .filter(FileAttachment.user_id == member.id)
            .count()
        )
        denied_upload = client.post(
            "/files/upload",
            params={"conversation_id": conversation.id},
            files={
                "file": (
                    "blocked-upload.txt",
                    b"Must not be stored after access revocation.",
                    "text/plain",
                )
            },
            headers=member_headers,
        )
        assert denied_upload.status_code == 404
        db_session.expire_all()
        assert (
            db_session.query(FileAttachment)
            .filter(FileAttachment.user_id == member.id)
            .count()
            == prior_count
        )

    # Workspace membership remains, but project access has been revoked.
    db_session.delete(project_membership)
    db_session.commit()
    assert_conversation_file_operations_denied()

    # Restore project membership, then revoke the workspace membership instead.
    db_session.add(
        ProjectMember(
            project_id=project_id,
            user_id=member.id,
            role=ProjectMemberRole.editor,
        )
    )
    db_session.commit()
    db_session.delete(workspace_membership)
    db_session.commit()
    assert_conversation_file_operations_denied()


@pytest.mark.parametrize(
    "member_name",
    [
        "../evil.xml",
        "..\\\\evil.xml",
        "/absolute.xml",
        "C:\\\\temp\\\\evil.xml",
    ],
)
def test_office_archive_rejects_unsafe_member_paths(tmp_path, member_name):
    from app.routers.files import _validate_office_archive

    path = tmp_path / "unsafe-office.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr(member_name, "payload")

    with pytest.raises(HTTPException) as error:
        _validate_office_archive(path, max_uncompressed=10_000)

    assert error.value.status_code == 415


def test_office_archive_rejects_excessive_member_count(tmp_path):
    from app.routers.files import _validate_office_archive

    path = tmp_path / "many-members.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for index in range(1001):
            archive.writestr(f"word/item-{index}.xml", "x")

    with pytest.raises(HTTPException, match="عددًا غير طبيعي") as error:
        _validate_office_archive(path, max_uncompressed=10_000)

    assert error.value.status_code == 415


def test_office_archive_rejects_excessive_total_uncompressed_size(tmp_path):
    from app.routers.files import _validate_office_archive

    path = tmp_path / "large-uncompressed.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("word/one.xml", "A" * 600)
        archive.writestr("word/two.xml", "B" * 600)

    with pytest.raises(HTTPException, match="غير المضغوط") as error:
        _validate_office_archive(path, max_uncompressed=1000)

    assert error.value.status_code == 415


def test_office_archive_rejects_abnormal_compression_ratio(tmp_path):
    from app.routers.files import _validate_office_archive

    path = tmp_path / "high-ratio.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "A" * 10_000)

    with pytest.raises(HTTPException, match="نسبة ضغط غير طبيعية") as error:
        _validate_office_archive(path, max_uncompressed=20_000)

    assert error.value.status_code == 415


def test_office_archive_rejects_malformed_zip(tmp_path):
    from app.routers.files import _validate_office_archive

    path = tmp_path / "malformed-office.zip"
    path.write_bytes(b"this is not a ZIP archive")

    with pytest.raises(HTTPException, match="تالف أو ليس ZIP صالحًا") as error:
        _validate_office_archive(path, max_uncompressed=10_000)

    assert error.value.status_code == 415


def test_office_archive_accepts_small_valid_package(tmp_path):
    from app.routers.files import _validate_office_archive

    path = tmp_path / "valid-office.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "<document>small</document>")
        archive.writestr("[Content_Types].xml", "<Types />")

    _validate_office_archive(path, max_uncompressed=10_000)
