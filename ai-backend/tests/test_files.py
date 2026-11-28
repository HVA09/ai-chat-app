"""
اختبارات المرحلة السادسة: رفع الملفات وإدارتها
"""

import pytest
from app.config import settings as app_settings
from app.routers import files as files_router


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



def test_upload_lock_failure_attempts_cleanup_without_masking_original_error(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    events = []

    def fail_user_lock(_db, _user_id):
        raise RuntimeError("user lock query failed")

    def fake_put_file(_path, object_key, _content_type):
        events.append(("stored", object_key))

    from types import SimpleNamespace
    from app.services.storage import StorageError

    def fail_cleanup(_object_key, _fallback_path):
        events.append(("cleanup_failed", None))
        raise StorageError("storage cleanup unavailable")

    monkeypatch.setattr(files_router, "lock_user_for_update", fail_user_lock)
    monkeypatch.setattr(files_router, "put_file", fake_put_file)
    monkeypatch.setattr(files_router, "delete_stored_file", fail_cleanup)
    monkeypatch.setattr(
        files_router,
        "enqueue_upload_cleanup_intent",
        lambda *_args, **_kwargs: SimpleNamespace(id="intent-1", status="pending"),
    )
    monkeypatch.setattr(
        files_router,
        "record_upload_cleanup_attempt",
        lambda *_args, **_kwargs: events.append(("outbox", None)),
    )

    token = _register_and_login(client, "upload-lock-failure@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with pytest.raises(RuntimeError, match="user lock query failed"):
        client.post(
            "/files/upload",
            files={"file": ("report.csv", b"name,value\\nalpha,1\\n", "text/csv")},
            headers=headers,
        )

    assert [event[0] for event in events] == ["stored", "cleanup_failed", "outbox"]


def test_upload_releases_db_before_storage_and_embedding_io(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    events = []
    monkeypatch.setattr(
        files_router,
        "commit_and_release_connection",
        lambda _db: events.append("release"),
    )
    monkeypatch.setattr(
        files_router,
        "put_file",
        lambda *_args, **_kwargs: events.append("storage"),
    )
    monkeypatch.setattr(
        files_router,
        "index_file_chunks",
        lambda _db, _file: (events.append("embedding") or 1),
    )

    token = _register_and_login(client, "upload-release@example.com")
    response = client.post(
        "/files/upload",
        files={"file": ("report.csv", b"name,value\nalpha,1\nbeta,2\n", "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert events == ["release", "storage", "release", "embedding"]


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
    events = []
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    upload_response = client.post("/files/upload", files={"file": ("note.csv", b"a,b,c\n1,2,3", "text/csv")}, headers=headers)
    assert upload_response.status_code == 201, upload_response.text
    file_id = upload_response.json()["id"]

    # Observe only the download boundary. Upload itself must use the real
    # commit/release helper so its attachment remains committed after an
    # embedding-provider failure rolls back the indexing transaction.
    monkeypatch.setattr(
        files_router,
        "commit_and_release_connection",
        lambda _db: events.append("release"),
    )
    original_open_file = files_router.open_file

    def track_open_file(*args, **kwargs):
        events.append("storage")
        return original_open_file(*args, **kwargs)

    monkeypatch.setattr(files_router, "open_file", track_open_file)
    events.clear()
    download_response = client.get(f"/files/{file_id}", headers=headers)
    assert download_response.status_code == 200
    assert download_response.content == b"a,b,c\n1,2,3"
    assert events == ["release", "storage"]


def test_delete_file_releases_db_before_object_storage_delete(
    client, tmp_path, monkeypatch
):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    events = []
    original_release = files_router.commit_and_release_connection
    original_delete = files_router.delete_stored_file

    def track_release(db):
        events.append("release")
        original_release(db)

    def track_storage_delete(*args, **kwargs):
        events.append("storage_delete")
        return original_delete(*args, **kwargs)

    monkeypatch.setattr(files_router, "commit_and_release_connection", track_release)
    monkeypatch.setattr(files_router, "delete_stored_file", track_storage_delete)

    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    upload_response = client.post(
        "/files/upload",
        files={"file": ("a.png", b"\x89PNG\r\n\x1a\n" + b"bytes", "image/png")},
        headers=headers,
    )
    assert upload_response.status_code == 201, upload_response.text
    file_id = upload_response.json()["id"]

    # Ignore upload's own release boundaries; assert the delete path order only.
    events.clear()
    delete_response = client.delete(f"/files/{file_id}", headers=headers)

    assert delete_response.status_code == 204
    assert events == ["release", "storage_delete"]
    assert client.get(f"/files/{file_id}", headers=headers).status_code == 404


def test_cannot_access_other_users_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token_a = _register_and_login(client, "filesowner@example.com")
    upload_response = client.post("/files/upload", files={"file": ("secret.pdf", b"%PDF-1.4 bytes", "application/pdf")}, headers={"Authorization": f"Bearer {token_a}"})
    file_id = upload_response.json()["id"]
    token_b = _register_and_login(client, "filesintruder@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    assert client.get(f"/files/{file_id}", headers=headers_b).status_code == 404
    assert client.delete(f"/files/{file_id}", headers=headers_b).status_code == 404


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



def test_project_upload_revalidates_project_after_storage_io(
    client, db_session, tmp_path, monkeypatch
):
    """An upload finishing after project deletion is discarded, not left workspace-scoped."""
    from app.models.file_attachment import FileAttachment
    from app.models.project import WorkspaceProject
    from app.models.user import User
    from app.routers import files as files_router

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client, "project-upload-race@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    owner = db_session.query(User).filter_by(
        email="project-upload-race@example.com"
    ).one()
    workspace = owner.owned_workspaces[0]
    project_id = client.post(
        "/projects",
        json={"workspace_id": workspace.id, "name": "Upload race"},
        headers=headers,
    ).json()["id"]

    objects = {}

    def fake_put_file(path, object_key, content_type):
        objects[object_key] = path.read_bytes()
        # Simulate the project disappearing while the upload is doing external
        # storage I/O, after its initial authorization check.
        db_session.query(WorkspaceProject).filter(
            WorkspaceProject.id == project_id
        ).delete(synchronize_session=False)
        db_session.commit()

    def fake_delete_file(object_key, fallback_path):
        objects.pop(object_key, None)
        fallback_path.unlink(missing_ok=True)

    monkeypatch.setattr(files_router, "put_file", fake_put_file)
    monkeypatch.setattr(files_router, "delete_stored_file", fake_delete_file)

    response = client.post(
        "/files/upload",
        params={"project_id": project_id},
        files={"file": ("late-upload.txt", b"late project content", "text/plain")},
        headers=headers,
    )

    assert response.status_code == 404
    assert objects == {}
    db_session.expire_all()
    assert db_session.query(FileAttachment).filter(
        FileAttachment.user_id == owner.id,
        FileAttachment.project_id == project_id,
    ).count() == 0

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




@pytest.mark.parametrize("delete_before_object_write", [True, False])
def test_personal_upload_cannot_orphan_object_during_account_deletion(
    db_session, tmp_path, monkeypatch, delete_before_object_write
):
    """Serialize personal-upload finalization with account deletion on PostgreSQL."""
    import asyncio
    from io import BytesIO
    from threading import Event, Thread
    from uuid import uuid4

    import pytest
    from sqlalchemy.orm import sessionmaker
    from starlette.datastructures import Headers, UploadFile

    from app.config import settings
    from app.models.file_attachment import FileAttachment
    from app.models.user import User
    from app.routers import files as files_router
    from app.routers import users as users_router
    from app.schemas.user import DeleteAccountRequest

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this regression test")

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(users_router, "verify_password", lambda *_args: True)
    monkeypatch.setattr(files_router, "extract_text", lambda *_args, **_kwargs: None)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    creator = session_factory()
    user = User(
        email=f"personal-upload-delete-{suffix}@example.test",
        hashed_password="test-only-hash",
    )
    creator.add(user)
    creator.commit()
    user_id = user.id
    creator.close()

    objects = {}
    put_started = Event()
    allow_object_write = Event()
    delete_finished = Event()
    upload_errors = []
    delete_errors = []

    def fake_put_file(path, object_key, _content_type):
        payload = path.read_bytes()
        put_started.set()
        if delete_before_object_write and not allow_object_write.wait(10):
            raise AssertionError("account deletion did not finish before object write")
        objects[object_key] = payload

    def fake_delete_file(object_key, fallback_path):
        objects.pop(object_key, None)
        fallback_path.unlink(missing_ok=True)

    def fake_delete_user_objects(_user_id):
        objects.clear()

    # Account deletion now commits a durable outbox row; run the real worker
    # synchronously in this concurrency test to verify the remote object is
    # removed after the transaction commits.
    from app import tasks
    from app.services import storage as storage_service

    monkeypatch.setattr(files_router, "put_file", fake_put_file)
    monkeypatch.setattr(files_router, "delete_stored_file", fake_delete_file)
    monkeypatch.setattr(storage_service, "delete_user_objects", fake_delete_user_objects)
    monkeypatch.setattr(
        users_router,
        "dispatch_storage_cleanup",
        lambda: tasks._run_storage_cleanup_outbox_batch(),
    )

    def run_upload():
        try:
            with session_factory() as upload_db:
                upload_db.begin()
                current_user = upload_db.get(User, user_id)
                upload = UploadFile(
                    filename="personal.txt",
                    file=BytesIO(b"personal upload during account deletion"),
                    headers=Headers({"content-type": "text/plain"}),
                )
                asyncio.run(
                    files_router.upload_file(
                        upload,
                        current_user=current_user,
                        db=upload_db,
                    )
                )
        except BaseException as exc:
            upload_errors.append(exc)

    def run_delete():
        try:
            with session_factory() as delete_db:
                delete_db.begin()
                current_user = delete_db.get(User, user_id)
                users_router.delete_account(
                    DeleteAccountRequest(password="test-password"),
                    current_user,
                    delete_db,
                )
        except BaseException as exc:
            delete_errors.append(exc)
        finally:
            delete_finished.set()

    upload_thread = None
    try:
        if delete_before_object_write:
            upload_thread = Thread(target=run_upload, daemon=True)
            upload_thread.start()
            assert put_started.wait(10), "personal upload did not reach storage I/O"

            delete_thread = Thread(target=run_delete, daemon=True)
            delete_thread.start()
            assert delete_finished.wait(10), "account deletion did not finish"
            allow_object_write.set()
            upload_thread.join(timeout=10)
            delete_thread.join(timeout=10)
            assert not upload_thread.is_alive()
            assert not delete_thread.is_alive()
            assert len(upload_errors) == 1
            from fastapi import HTTPException
            assert isinstance(upload_errors[0], HTTPException)
            assert upload_errors[0].status_code == 404
        else:
            run_upload()
            assert upload_errors == []
            assert len(objects) == 1
            run_delete()
            assert delete_finished.is_set()

        assert delete_errors == []
        assert objects == {}
        with session_factory() as verify:
            assert verify.get(User, user_id) is None
            assert verify.query(FileAttachment).filter(
                FileAttachment.user_id == user_id
            ).count() == 0
    finally:
        allow_object_write.set()
        if upload_thread is not None:
            upload_thread.join(timeout=10)
        with session_factory() as cleanup:
            cleanup.query(User).filter(User.id == user_id).delete()
            cleanup.commit()


def test_account_delete_holds_user_lock_until_audit_commit_on_postgres(
    db_session, tmp_path, monkeypatch
):
    """The account lock must survive audit insertion until deletion commits."""
    from threading import Event, Thread
    from uuid import uuid4

    import pytest
    from sqlalchemy.orm import sessionmaker

    from app.config import settings
    from app.models.audit_log import AuditLog
    from app.models.user import User
    from app.routers import users as users_router
    from app.schemas.user import DeleteAccountRequest
    from app.services.project_file_retention import lock_user_for_update

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this regression test")

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(users_router, "verify_password", lambda *_args: True)
    monkeypatch.setattr(users_router, "dispatch_storage_cleanup", lambda: None)
    monkeypatch.setattr(
        users_router, "privatize_account_workspace_attachments", lambda *_args: None
    )

    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    with session_factory() as creator:
        user = User(
            email=f"account-delete-audit-{suffix}@example.test",
            hashed_password="test-only-hash",
        )
        creator.add(user)
        creator.commit()
        user_id = user.id

    audit_inserted = Event()
    allow_delete_commit = Event()
    lock_attempt_started = Event()
    lock_attempt_finished = Event()
    delete_errors = []
    lock_results = []
    success_logs = []
    original_log_event = users_router.log_event

    def pause_after_audit_insert(db, event_type, description, user_id=None,
                                 workspace_id=None, **kwargs):
        original_log_event(
            db, event_type, description, user_id, workspace_id, **kwargs
        )
        if event_type == "account_deleted":
            audit_inserted.set()
            if not allow_delete_commit.wait(10):
                raise AssertionError("test did not release account deletion")

    monkeypatch.setattr(users_router, "log_event", pause_after_audit_insert)
    monkeypatch.setattr(
        users_router.logger, "info", lambda *args, **_kwargs: success_logs.append(args)
    )

    def run_delete():
        try:
            with session_factory() as delete_db:
                current_user = delete_db.get(User, user_id)
                users_router.delete_account(
                    DeleteAccountRequest(password="test-password"),
                    current_user,
                    delete_db,
                )
        except BaseException as exc:
            delete_errors.append(exc)

    def try_user_lock():
        try:
            with session_factory() as contender_db:
                lock_attempt_started.set()
                lock_results.append(lock_user_for_update(contender_db, user_id))
                contender_db.rollback()
        except BaseException as exc:
            lock_results.append(exc)
        finally:
            lock_attempt_finished.set()

    delete_thread = Thread(target=run_delete, daemon=True)
    contender_thread = Thread(target=try_user_lock, daemon=True)
    try:
        delete_thread.start()
        assert audit_inserted.wait(10), "account deletion did not reach audit insertion"

        contender_thread.start()
        assert lock_attempt_started.wait(10), "lock contender did not start"
        # The contender must remain blocked while the deletion transaction is open.
        assert not lock_attempt_finished.wait(0.5), (
            "account row lock was released before account deletion committed"
        )
        assert success_logs == [], "success log was emitted before commit"

        allow_delete_commit.set()
        delete_thread.join(timeout=10)
        contender_thread.join(timeout=10)
        assert not delete_thread.is_alive()
        assert not contender_thread.is_alive()
        assert delete_errors == []
        assert lock_results == [False]
        assert len(success_logs) == 1

        with session_factory() as verify:
            assert verify.get(User, user_id) is None
            audit = (
                verify.query(AuditLog)
                .filter(AuditLog.event_type == "account_deleted")
                .filter(AuditLog.description == f"حذف حساب: account-delete-audit-{suffix}@example.test")
                .one()
            )
            assert audit.user_id is None
    finally:
        allow_delete_commit.set()
        delete_thread.join(timeout=10)
        contender_thread.join(timeout=10)
        with session_factory() as cleanup:
            cleanup.query(User).filter(User.id == user_id).delete()
            cleanup.query(AuditLog).filter(
                AuditLog.description == f"حذف حساب: account-delete-audit-{suffix}@example.test"
            ).delete()
            cleanup.commit()



def test_personal_upload_indexing_cannot_outlive_account_deletion(
    db_session, tmp_path, monkeypatch
):
    """A late embedding result cannot recreate chunks after account deletion."""
    import asyncio
    from io import BytesIO
    from threading import Event, Thread
    from uuid import uuid4

    import pytest
    from fastapi import HTTPException
    from sqlalchemy.orm import sessionmaker
    from starlette.datastructures import Headers, UploadFile

    from app.config import settings
    from app.models.file_attachment import FileAttachment
    from app.models.file_chunk import FileChunk
    from app.models.user import User
    from app.routers import files as files_router
    from app.routers import users as users_router
    from app.schemas.user import DeleteAccountRequest
    from app.services import rag as rag_service

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL foreign-key and transaction behavior is required")

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(users_router, "verify_password", lambda *_args: True)
    monkeypatch.setattr(files_router, "extract_text", lambda *_args, **_kwargs: "index this personal file")
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    suffix = uuid4().hex
    creator = session_factory()
    user = User(
        email=f"personal-index-delete-{suffix}@example.test",
        hashed_password="test-only-hash",
    )
    creator.add(user)
    creator.commit()
    user_id = user.id
    creator.close()

    objects = {}
    indexing_started = Event()
    allow_indexing = Event()
    deletion_finished = Event()
    upload_errors = []
    deletion_errors = []
    indexed_file_ids = []
    original_index = files_router.index_file_chunks

    def fake_put_file(path, object_key, _content_type):
        objects[object_key] = path.read_bytes()

    def fake_delete_user_objects(_user_id):
        objects.clear()

    def delayed_index(db, attachment):
        indexed_file_ids.append(attachment.id)
        indexing_started.set()
        if not allow_indexing.wait(10):
            raise AssertionError("test did not release the embedding/indexing phase")
        return original_index(db, attachment)

    from app import tasks
    from app.services import storage as storage_service

    monkeypatch.setattr(files_router, "put_file", fake_put_file)
    monkeypatch.setattr(storage_service, "delete_user_objects", fake_delete_user_objects)
    monkeypatch.setattr(
        users_router,
        "dispatch_storage_cleanup",
        lambda: tasks._run_storage_cleanup_outbox_batch(),
    )
    monkeypatch.setattr(files_router, "index_file_chunks", delayed_index)
    monkeypatch.setattr(
        rag_service,
        "embed_documents_sync",
        lambda chunks: [[0.0] * 768 for _ in chunks],
    )

    def run_upload():
        try:
            with session_factory() as upload_db:
                upload_db.begin()
                current_user = upload_db.get(User, user_id)
                upload = UploadFile(
                    filename="personal.txt",
                    file=BytesIO(b"personal file with extracted text"),
                    headers=Headers({"content-type": "text/plain"}),
                )
                asyncio.run(
                    files_router.upload_file(
                        upload,
                        current_user=current_user,
                        db=upload_db,
                    )
                )
        except BaseException as exc:
            upload_errors.append(exc)

    def run_delete():
        try:
            with session_factory() as delete_db:
                delete_db.begin()
                current_user = delete_db.get(User, user_id)
                users_router.delete_account(
                    DeleteAccountRequest(password="test-password"),
                    current_user,
                    delete_db,
                )
        except BaseException as exc:
            deletion_errors.append(exc)
        finally:
            deletion_finished.set()

    upload_thread = Thread(target=run_upload, daemon=True)
    deletion_thread = None
    try:
        upload_thread.start()
        assert indexing_started.wait(10), "upload did not reach the indexing phase"

        # The upload has committed its attachment and released the user lock
        # before the external embedding operation. Deletion must finish first.
        deletion_thread = Thread(target=run_delete, daemon=True)
        deletion_thread.start()
        assert deletion_finished.wait(10), "account deletion did not finish"
        assert deletion_errors == []
        allow_indexing.set()

        upload_thread.join(timeout=10)
        deletion_thread.join(timeout=10)
        assert not upload_thread.is_alive()
        assert not deletion_thread.is_alive()
        assert len(upload_errors) == 1
        assert isinstance(upload_errors[0], HTTPException)
        assert upload_errors[0].status_code == 404
        assert objects == {}

        with session_factory() as verify:
            assert verify.get(User, user_id) is None
            assert verify.query(FileAttachment).filter(
                FileAttachment.user_id == user_id
            ).count() == 0
            assert len(indexed_file_ids) == 1
            assert verify.query(FileChunk).filter(
                FileChunk.file_id == indexed_file_ids[0]
            ).count() == 0
    finally:
        allow_indexing.set()
        upload_thread.join(timeout=10)
        if deletion_thread is not None:
            deletion_thread.join(timeout=10)
        with session_factory() as cleanup:
            cleanup.query(User).filter(User.id == user_id).delete()
            cleanup.commit()



def test_personal_upload_embedding_failure_after_account_deletion_is_clean_404(
    db_session, tmp_path, monkeypatch
):
    """A provider failure after deletion must not audit or finalize a deleted upload."""
    import asyncio
    from io import BytesIO
    from threading import Event, Thread
    from uuid import uuid4

    import pytest
    from fastapi import HTTPException
    from sqlalchemy.orm import sessionmaker
    from starlette.datastructures import Headers, UploadFile

    from app.config import settings
    from app.models.file_attachment import FileAttachment
    from app.models.file_chunk import FileChunk
    from app.models.user import User
    from app.routers import files as files_router
    from app.routers import users as users_router
    from app.schemas.user import DeleteAccountRequest
    from app.services.embeddings import EmbeddingServiceError

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock and cascade behavior is required")

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(users_router, "verify_password", lambda *_args: True)
    monkeypatch.setattr(files_router, "extract_text", lambda *_args, **_kwargs: "index this personal file")
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    suffix = uuid4().hex
    creator = session_factory()
    user = User(
        email=f"personal-embedding-error-delete-{suffix}@example.test",
        hashed_password="test-only-hash",
    )
    creator.add(user)
    creator.commit()
    user_id = user.id
    creator.close()

    objects = {}
    indexing_started = Event()
    allow_indexing_failure = Event()
    deletion_finished = Event()
    upload_errors = []
    deletion_errors = []
    indexed_file_ids = []
    upload_audit_attempts = []

    def fake_put_file(path, object_key, _content_type):
        objects[object_key] = path.read_bytes()

    def fake_delete_file(object_key, fallback_path):
        objects.pop(object_key, None)
        fallback_path.unlink(missing_ok=True)

    def fake_delete_user_objects(_user_id):
        objects.clear()

    def fail_index_after_delete(_db, attachment):
        indexed_file_ids.append(attachment.id)
        indexing_started.set()
        if not allow_indexing_failure.wait(10):
            raise AssertionError("test did not release the embedding failure")
        raise EmbeddingServiceError("simulated provider failure after account deletion")

    from app import tasks
    from app.services import storage as storage_service

    monkeypatch.setattr(files_router, "put_file", fake_put_file)
    monkeypatch.setattr(files_router, "delete_stored_file", fake_delete_file)
    monkeypatch.setattr(storage_service, "delete_user_objects", fake_delete_user_objects)
    monkeypatch.setattr(
        users_router,
        "dispatch_storage_cleanup",
        lambda: tasks._run_storage_cleanup_outbox_batch(),
    )
    monkeypatch.setattr(files_router, "index_file_chunks", fail_index_after_delete)
    monkeypatch.setattr(
        files_router,
        "log_event",
        lambda *_args, **_kwargs: upload_audit_attempts.append("called"),
    )

    def run_upload():
        try:
            with session_factory() as upload_db:
                upload_db.begin()
                current_user = upload_db.get(User, user_id)
                upload = UploadFile(
                    filename="personal.txt",
                    file=BytesIO(b"personal file that will fail embedding"),
                    headers=Headers({"content-type": "text/plain"}),
                )
                asyncio.run(
                    files_router.upload_file(
                        upload,
                        current_user=current_user,
                        db=upload_db,
                    )
                )
        except BaseException as exc:
            upload_errors.append(exc)

    def run_delete():
        try:
            with session_factory() as delete_db:
                delete_db.begin()
                current_user = delete_db.get(User, user_id)
                users_router.delete_account(
                    DeleteAccountRequest(password="test-password"),
                    current_user,
                    delete_db,
                )
        except BaseException as exc:
            deletion_errors.append(exc)
        finally:
            deletion_finished.set()

    upload_thread = Thread(target=run_upload, daemon=True)
    deletion_thread = None
    try:
        upload_thread.start()
        assert indexing_started.wait(10), "upload did not reach external embedding"

        deletion_thread = Thread(target=run_delete, daemon=True)
        deletion_thread.start()
        assert deletion_finished.wait(10), "account deletion did not finish"
        assert deletion_errors == []
        allow_indexing_failure.set()

        upload_thread.join(timeout=10)
        deletion_thread.join(timeout=10)
        assert not upload_thread.is_alive()
        assert not deletion_thread.is_alive()
        assert len(upload_errors) == 1
        assert isinstance(upload_errors[0], HTTPException)
        assert upload_errors[0].status_code == 404
        assert upload_audit_attempts == []
        assert objects == {}

        with session_factory() as verify:
            assert verify.get(User, user_id) is None
            assert verify.query(FileAttachment).filter(
                FileAttachment.user_id == user_id
            ).count() == 0
            assert len(indexed_file_ids) == 1
            assert verify.query(FileChunk).filter(
                FileChunk.file_id == indexed_file_ids[0]
            ).count() == 0
    finally:
        allow_indexing_failure.set()
        upload_thread.join(timeout=10)
        if deletion_thread is not None:
            deletion_thread.join(timeout=10)
        with session_factory() as cleanup:
            cleanup.query(User).filter(User.id == user_id).delete()
            cleanup.commit()


def test_project_upload_finalization_waits_for_project_deletion_on_postgres(
    db_session, tmp_path, monkeypatch
):
    """A two-session upload finishing after project deletion is discarded safely."""
    import asyncio
    from io import BytesIO
    from threading import Event, Thread
    from uuid import uuid4

    import pytest
    from sqlalchemy.orm import sessionmaker
    from starlette.datastructures import Headers, UploadFile

    from app.config import settings
    from app.models.file_attachment import FileAttachment
    from app.models.project import WorkspaceProject
    from app.models.user import User
    from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
    from app.routers import files as files_router
    from app.routers import projects as projects_router

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this regression test")

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    creator = session_factory()
    user = User(
        email=f"upload-delete-{suffix}@example.test",
        hashed_password="test-only-hash",
    )
    creator.add(user)
    creator.flush()
    workspace = Workspace(owner_id=user.id, name=f"Upload delete {suffix[:12]}")
    creator.add(workspace)
    creator.flush()
    creator.add(
        WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=WorkspaceRole.owner,
        )
    )
    project = WorkspaceProject(
        workspace_id=workspace.id,
        owner_id=user.id,
        name=f"Project {suffix[:12]}",
    )
    creator.add(project)
    creator.commit()
    user_id, workspace_id, project_id = user.id, workspace.id, project.id
    creator.close()

    allow_upload_to_finalize = Event()
    delete_finished = Event()
    delete_errors = []
    upload_errors = []
    objects = {}

    def delete_project_during_upload():
        try:
            with session_factory() as delete_db:
                delete_db.begin()
                current_user = delete_db.get(User, user_id)
                projects_router.delete_project(project_id, current_user, delete_db)
        except BaseException as exc:
            delete_errors.append(exc)
        finally:
            delete_finished.set()
            allow_upload_to_finalize.set()

    deletion_thread = Thread(target=delete_project_during_upload, daemon=True)

    def fake_put_file(path, object_key, content_type):
        objects[object_key] = path.read_bytes()
        # Start deletion only after upload has passed initial authorization and
        # reached external storage I/O, with its database connection released.
        deletion_thread.start()
        if not delete_finished.wait(10):
            raise AssertionError("project deletion did not finish during storage I/O")

    def fake_delete_file(object_key, fallback_path):
        objects.pop(object_key, None)
        fallback_path.unlink(missing_ok=True)

    monkeypatch.setattr(files_router, "put_file", fake_put_file)
    monkeypatch.setattr(files_router, "delete_stored_file", fake_delete_file)
    monkeypatch.setattr(files_router, "extract_text", lambda *_args, **_kwargs: None)

    try:
        with session_factory() as upload_db:
            upload_db.begin()
            current_user = upload_db.get(User, user_id)
            upload = UploadFile(
                filename="late-upload.txt",
                file=BytesIO(b"late project content"),
                headers=Headers({"content-type": "text/plain"}),
            )
            try:
                asyncio.run(
                    files_router.upload_file(
                        upload,
                        project_id=project_id,
                        current_user=current_user,
                        db=upload_db,
                    )
                )
            except BaseException as exc:
                upload_errors.append(exc)
            finally:
                upload_db.rollback()

        assert delete_finished.is_set()
        assert delete_errors == []
        assert len(upload_errors) == 1
        from fastapi import HTTPException
        assert isinstance(upload_errors[0], HTTPException)
        assert upload_errors[0].status_code == 404
        assert objects == {}
        deletion_thread.join(timeout=5)
        assert not deletion_thread.is_alive()

        with session_factory() as verify:
            assert verify.get(WorkspaceProject, project_id) is None
            assert verify.query(FileAttachment).filter(
                FileAttachment.user_id == user_id,
                FileAttachment.project_id == project_id,
            ).count() == 0
            assert verify.query(FileAttachment).filter(
                FileAttachment.user_id == user_id,
                FileAttachment.workspace_id == workspace_id,
            ).count() == 0
    finally:
        allow_upload_to_finalize.set()
        if deletion_thread.ident is not None:
            deletion_thread.join(timeout=5)
        with session_factory() as cleanup:
            cleanup.query(User).filter(User.id == user_id).delete()
            cleanup.commit()

def test_upload_rechecks_file_count_quota_after_account_lock(
    client, db_session, tmp_path, monkeypatch
):
    """A quota reached while storage I/O is in progress rejects and cleans the upload."""
    from app.models.file_attachment import FileAttachment

    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(app_settings, "MAX_FILES_PER_USER", 1)
    objects = {}

    def fake_put_file(path, object_key, _content_type):
        objects[object_key] = path.read_bytes()

    def fake_delete_file(object_key, fallback_path):
        objects.pop(object_key, None)
        fallback_path.unlink(missing_ok=True)

    def acquire_lock_after_competing_upload(_db, _user_id):
        # The initial quota check has already passed. Model a concurrent upload
        # consuming the last slot before this request acquires the user lock.
        monkeypatch.setattr(app_settings, "MAX_FILES_PER_USER", 0)
        return True

    monkeypatch.setattr(files_router, "put_file", fake_put_file)
    monkeypatch.setattr(files_router, "delete_stored_file", fake_delete_file)
    monkeypatch.setattr(
        files_router, "lock_user_for_update", acquire_lock_after_competing_upload
    )

    token = _register_and_login(client, "upload-quota-race@example.com")
    response = client.post(
        "/files/upload",
        files={"file": ("second.txt", b"second upload", "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "وصلت للحد الأقصى لعدد الملفات"
    assert objects == {}
    assert db_session.query(FileAttachment).filter(
        FileAttachment.original_filename == "second.txt"
    ).count() == 0


@pytest.mark.parametrize("quota_kind", ["file_count", "storage_bytes"])
def test_concurrent_uploads_cannot_exceed_account_quota_on_postgres(
    db_session, tmp_path, monkeypatch, quota_kind
):
    """Two independent uploads racing for the final quota slot serialize at the user lock."""
    import asyncio
    from io import BytesIO
    from threading import Barrier, Thread
    from uuid import uuid4

    import pytest
    from fastapi import HTTPException
    from sqlalchemy.orm import sessionmaker
    from starlette.datastructures import Headers, UploadFile

    from app.config import settings
    from app.models.file_attachment import FileAttachment
    from app.models.user import User
    from app.routers import files as files_router

    bind = db_session.get_bind()
    engine = bind.engine if hasattr(bind, "engine") else bind
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock behavior is required for this regression test")

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "MAX_FILES_PER_USER", 1 if quota_kind == "file_count" else 10)
    monkeypatch.setattr(settings, "MAX_STORAGE_PER_USER_MB", 1)
    monkeypatch.setattr(files_router, "extract_text", lambda *_args, **_kwargs: None)

    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    creator = session_factory()
    user = User(
        email=f"concurrent-quota-{suffix}@example.test",
        hashed_password="test-only-hash",
    )
    creator.add(user)
    creator.commit()
    user_id = user.id
    creator.close()

    # Both requests must finish the initial quota check and reach external
    # storage before either is allowed to finalize under the user row lock.
    storage_barrier = Barrier(2)
    objects = {}
    upload_results = []
    upload_errors = []

    def fake_put_file(local_path, object_key, _content_type):
        storage_barrier.wait(timeout=10)
        objects[object_key] = local_path.read_bytes()

    def fake_delete_file(object_key, fallback_path):
        objects.pop(object_key, None)
        fallback_path.unlink(missing_ok=True)

    monkeypatch.setattr(files_router, "put_file", fake_put_file)
    monkeypatch.setattr(files_router, "delete_stored_file", fake_delete_file)

    payloads = (
        b"first concurrent upload",
        b"second concurrent upload",
    )
    if quota_kind == "storage_bytes":
        # A 1 MiB account limit; each upload is 600 KiB, so only one may commit.
        payloads = (b"a" * (600 * 1024), b"b" * (600 * 1024))

    def run_upload(index, payload):
        try:
            with session_factory() as upload_db:
                upload_db.begin()
                current_user = upload_db.get(User, user_id)
                upload = UploadFile(
                    filename=f"quota-{index}.txt",
                    file=BytesIO(payload),
                    headers=Headers({"content-type": "text/plain"}),
                )
                result = asyncio.run(
                    files_router.upload_file(
                        upload,
                        current_user=current_user,
                        db=upload_db,
                    )
                )
                upload_results.append(result)
        except BaseException as exc:
            upload_errors.append(exc)

    threads = [
        Thread(target=run_upload, args=(index, payload), daemon=True)
        for index, payload in enumerate(payloads)
    ]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        assert all(not thread.is_alive() for thread in threads), "upload threads did not finish"

        assert len(upload_results) == 1
        assert len(upload_errors) == 1
        assert isinstance(upload_errors[0], HTTPException)
        assert upload_errors[0].status_code == 413

        with session_factory() as verify:
            saved = (
                verify.query(FileAttachment)
                .filter(FileAttachment.user_id == user_id)
                .all()
            )
            assert len(saved) == 1
            if quota_kind == "storage_bytes":
                assert sum(item.size_bytes for item in saved) <= 1024 * 1024
        assert len(objects) == 1
    finally:
        # Ensure a failed test cannot leave worker threads blocked at the barrier.
        try:
            storage_barrier.abort()
        except Exception:
            pass
        for thread in threads:
            thread.join(timeout=5)
        with session_factory() as cleanup:
            cleanup.query(FileAttachment).filter(
                FileAttachment.user_id == user_id
            ).delete(synchronize_session=False)
            cleanup.query(User).filter(User.id == user_id).delete(
                synchronize_session=False
            )
            cleanup.commit()
