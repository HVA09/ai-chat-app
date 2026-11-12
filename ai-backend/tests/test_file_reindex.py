"""Per-file RAG reindex authorization and atomic replacement tests."""

from datetime import datetime, timezone

import pytest

from app.models.file_attachment import FileAttachment, extracted_text_fingerprint
from app.models.file_chunk import FileChunk
from app.models.project_member import ProjectMember, ProjectMemberRole
from app.models.user import User
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.routers import files as files_router
from app.services.embeddings import EmbeddingServiceError
from app.services.rag import PreparedFileIndex, persist_file_index


def _register_and_login(client, email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _add_file(
    db_session,
    *,
    user_id: int,
    text: str,
    workspace_id: int | None = None,
    project_id: int | None = None,
) -> FileAttachment:
    file = FileAttachment(
        user_id=user_id,
        workspace_id=workspace_id,
        project_id=project_id,
        original_filename="knowledge.txt",
        stored_filename=f"knowledge-{user_id}-{project_id or 'personal'}.txt",
        content_type="text/plain",
        size_bytes=len(text.encode("utf-8")),
        extracted_text=text,
        extracted_text_sha256=extracted_text_fingerprint(text),
        indexed_text_sha256="0" * 64,
        indexed_embedding_fingerprint="1" * 64,
        indexed_embedding_provider="old-provider",
        indexed_embedding_model="old-model",
        indexed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(file)
    db_session.flush()
    db_session.add(
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            content="old indexed content",
            embedding=[0.1] * 768,
        )
    )
    db_session.commit()
    return file


def _prepared(text: str, chunk: str = "replacement chunk") -> PreparedFileIndex:
    return PreparedFileIndex(
        text_fingerprint=extracted_text_fingerprint(text),
        chunks=(chunk,),
        embeddings=(tuple([0.2] * 768),),
        provider="test-provider",
        model="test-embedding-model",
        embedding_fingerprint="2" * 64,
    )


def _disable_reindex_quotas(monkeypatch):
    monkeypatch.setattr(
        files_router,
        "enforce_daily_ai_limit",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        files_router,
        "enforce_workspace_daily_ai_limit",
        lambda *_args, **_kwargs: None,
    )


def test_personal_file_reindex_replaces_chunks_and_updates_fingerprints(
    client, db_session, monkeypatch
):
    token = _register_and_login(client, "personal-file-reindex@example.com")
    user = db_session.query(User).filter_by(
        email="personal-file-reindex@example.com"
    ).one()
    file = _add_file(
        db_session,
        user_id=user.id,
        text="The current extracted source text.",
    )
    _disable_reindex_quotas(monkeypatch)

    events = []
    original_release = files_router.commit_and_release_connection

    def tracked_release(db):
        events.append("release")
        original_release(db)

    def prepare(text):
        events.append("embeddings")
        return _prepared(text, "fresh replacement content")

    monkeypatch.setattr(
        files_router, "commit_and_release_connection", tracked_release
    )
    monkeypatch.setattr(files_router, "prepare_file_index", prepare)

    response = client.post(
        f"/files/{file.id}/reindex",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_ai_indexed"] is True
    assert events == ["release", "embeddings"]

    db_session.expire_all()
    chunks = (
        db_session.query(FileChunk)
        .filter(FileChunk.file_id == file.id)
        .order_by(FileChunk.chunk_index)
        .all()
    )
    refreshed = db_session.get(FileAttachment, file.id)

    assert [chunk.content for chunk in chunks] == ["fresh replacement content"]
    assert refreshed.indexed_text_sha256 == extracted_text_fingerprint(
        refreshed.extracted_text
    )
    assert refreshed.indexed_embedding_fingerprint == "2" * 64
    assert refreshed.indexed_embedding_provider == "test-provider"
    assert refreshed.indexed_embedding_model == "test-embedding-model"
    assert refreshed.indexed_at is not None


def test_embedding_failure_preserves_previous_chunks_and_metadata(
    client, db_session, monkeypatch
):
    token = _register_and_login(client, "reindex-provider-failure@example.com")
    user = db_session.query(User).filter_by(
        email="reindex-provider-failure@example.com"
    ).one()
    file = _add_file(
        db_session,
        user_id=user.id,
        text="Source text whose old index must remain available.",
    )
    _disable_reindex_quotas(monkeypatch)

    def fail_prepare(_text):
        raise EmbeddingServiceError("simulated provider outage")

    monkeypatch.setattr(files_router, "prepare_file_index", fail_prepare)

    response = client.post(
        f"/files/{file.id}/reindex",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 503
    assert "الفهرس السابق" in response.json()["detail"]

    db_session.expire_all()
    chunks = db_session.query(FileChunk).filter(FileChunk.file_id == file.id).all()
    refreshed = db_session.get(FileAttachment, file.id)

    assert len(chunks) == 1
    assert chunks[0].content == "old indexed content"
    assert refreshed.indexed_text_sha256 == "0" * 64
    assert refreshed.indexed_embedding_fingerprint == "1" * 64
    assert refreshed.indexed_embedding_provider == "old-provider"
    assert refreshed.indexed_embedding_model == "old-model"


def test_project_viewer_cannot_reindex_but_project_editor_can(
    client, db_session, monkeypatch
):
    owner_token = _register_and_login(client, "reindex-project-owner@example.com")
    owner = db_session.query(User).filter_by(
        email="reindex-project-owner@example.com"
    ).one()
    workspace = owner.owned_workspaces[0]
    project_response = client.post(
        "/projects",
        json={"workspace_id": workspace.id, "name": "Reindex ACL Project"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    viewer_token = _register_and_login(client, "reindex-project-viewer@example.com")
    viewer = db_session.query(User).filter_by(
        email="reindex-project-viewer@example.com"
    ).one()
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=viewer.id,
        role=WorkspaceRole.member,
    )
    project_membership = ProjectMember(
        project_id=project_id,
        user_id=viewer.id,
        role=ProjectMemberRole.viewer,
    )
    db_session.add_all([membership, project_membership])
    db_session.commit()

    file = _add_file(
        db_session,
        user_id=owner.id,
        workspace_id=workspace.id,
        project_id=project_id,
        text="Project knowledge available to editors.",
    )
    _disable_reindex_quotas(monkeypatch)
    prepared_calls = []

    def prepare(text):
        prepared_calls.append(text)
        return _prepared(text)

    monkeypatch.setattr(files_router, "prepare_file_index", prepare)
    headers = {"Authorization": f"Bearer {viewer_token}"}

    denied = client.post(f"/files/{file.id}/reindex", headers=headers)
    assert denied.status_code == 403
    assert prepared_calls == []

    project_membership.role = ProjectMemberRole.editor
    db_session.commit()

    allowed = client.post(f"/files/{file.id}/reindex", headers=headers)
    assert allowed.status_code == 200, allowed.text
    assert prepared_calls == ["Project knowledge available to editors."]


def test_workspace_member_needs_files_manage_for_another_users_file(
    client, db_session, monkeypatch
):
    owner_token = _register_and_login(client, "reindex-workspace-owner@example.com")
    owner = db_session.query(User).filter_by(
        email="reindex-workspace-owner@example.com"
    ).one()
    workspace = owner.owned_workspaces[0]

    member_token = _register_and_login(client, "reindex-workspace-member@example.com")
    member = db_session.query(User).filter_by(
        email="reindex-workspace-member@example.com"
    ).one()
    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=member.id,
        role=WorkspaceRole.member,
    )
    db_session.add(membership)
    db_session.commit()

    file = _add_file(
        db_session,
        user_id=owner.id,
        workspace_id=workspace.id,
        text="Shared workspace knowledge.",
    )
    _disable_reindex_quotas(monkeypatch)
    monkeypatch.setattr(
        files_router,
        "prepare_file_index",
        lambda text: _prepared(text),
    )
    headers = {"Authorization": f"Bearer {member_token}"}

    denied = client.post(f"/files/{file.id}/reindex", headers=headers)
    assert denied.status_code == 403

    membership.role = WorkspaceRole.admin
    db_session.commit()
    allowed = client.post(f"/files/{file.id}/reindex", headers=headers)
    assert allowed.status_code == 200, allowed.text


def test_persist_file_index_rejects_a_changed_source_before_deleting_chunks(
    db_session,
):
    user = User(email="reindex-source-change@example.com", hashed_password="hashed")
    db_session.add(user)
    db_session.flush()
    file = _add_file(
        db_session,
        user_id=user.id,
        text="Original text used to build vectors.",
    )
    prepared = _prepared(file.extracted_text, "prepared from the original source")

    file.extracted_text = "The source changed after embeddings were generated."
    with pytest.raises(EmbeddingServiceError, match="تغيّر نص الملف"):
        persist_file_index(db_session, file, prepared)

    old_chunks = (
        db_session.query(FileChunk)
        .filter(FileChunk.file_id == file.id)
        .all()
    )
    assert len(old_chunks) == 1
    assert old_chunks[0].content == "old indexed content"
