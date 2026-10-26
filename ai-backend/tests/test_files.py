"""
اختبارات المرحلة السادسة: رفع الملفات وإدارتها
"""
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

