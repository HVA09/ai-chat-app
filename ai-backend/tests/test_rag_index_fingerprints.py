"""Regression tests for invalidating stale RAG indexes."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.models.conversation import Conversation
from app.models.file_attachment import FileAttachment, extracted_text_fingerprint
from app.models.file_chunk import FileChunk
from app.models.user import User
from app.models.workspace import Workspace
from app.services import rag


@pytest.mark.parametrize("stale_field", ["indexed_text_sha256", "indexed_embedding_fingerprint"])
def test_retrieval_skips_stale_index_without_calling_embedding_provider(
    db_session, monkeypatch, stale_field
):
    """Old vectors must be excluded after source text or embedding identity changes."""
    user = User(
        email=f"rag-stale-{stale_field}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    db_session.flush()

    workspace = Workspace(owner_id=user.id, name=f"Stale index {stale_field}")
    db_session.add(workspace)
    db_session.flush()

    conversation = Conversation(
        user_id=user.id,
        workspace_id=workspace.id,
        title="Stale RAG index regression",
    )
    db_session.add(conversation)
    db_session.flush()

    file = FileAttachment(
        user_id=user.id,
        workspace_id=workspace.id,
        project_id=None,
        original_filename="notes.txt",
        stored_filename=f"stale-{stale_field}.txt",
        content_type="text/plain",
        size_bytes=32,
        extracted_text="Current source text used for indexing.",
    )
    db_session.add(file)
    db_session.flush()

    active_fingerprint = "current-embedding-fingerprint"
    source_fingerprint = extracted_text_fingerprint(file.extracted_text)
    file.indexed_text_sha256 = source_fingerprint
    file.indexed_embedding_fingerprint = active_fingerprint
    file.indexed_embedding_provider = "test-provider"
    file.indexed_embedding_model = "test-model"
    if stale_field == "indexed_text_sha256":
        file.indexed_text_sha256 = "old-source-fingerprint"
    else:
        file.indexed_embedding_fingerprint = "old-embedding-fingerprint"

    db_session.add(
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            content="Old indexed text that must not be retrieved.",
            embedding=[0.1] * 768,
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        rag,
        "get_embedding_index_identity",
        lambda: ("test-provider", "test-model", active_fingerprint),
    )
    embed_query = AsyncMock(
        side_effect=AssertionError("Stale index must be filtered before embedding the query.")
    )
    monkeypatch.setattr(rag, "embed_query", embed_query)

    rows = asyncio.run(
        rag.retrieve_relevant_chunks(
            db_session,
            user.id,
            conversation.id,
            "What is in the notes?",
            workspace_id=workspace.id,
        )
    )

    assert rows == []
    embed_query.assert_not_awaited()


def test_reindex_replaces_previous_chunks_and_updates_fingerprints(
    db_session, monkeypatch
):
    """A successful reindex atomically replaces stale chunks and records identity."""
    user = User(email="rag-reindex-replace@example.com", hashed_password="hashed")
    db_session.add(user)
    db_session.flush()

    workspace = Workspace(owner_id=user.id, name="Reindex replacement")
    db_session.add(workspace)
    db_session.flush()

    file = FileAttachment(
        user_id=user.id,
        workspace_id=workspace.id,
        project_id=None,
        original_filename="notes.txt",
        stored_filename="rag-reindex-replace.txt",
        content_type="text/plain",
        size_bytes=64,
        extracted_text="Old indexed source text.",
    )
    db_session.add(file)
    db_session.flush()

    old_source_fingerprint = extracted_text_fingerprint(file.extracted_text)
    file.indexed_text_sha256 = old_source_fingerprint
    file.indexed_embedding_fingerprint = "old-model-fingerprint"
    file.indexed_embedding_provider = "old-provider"
    file.indexed_embedding_model = "old-model"
    db_session.add(
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            content="Old indexed source text.",
            embedding=[0.1] * 768,
        )
    )
    db_session.commit()

    current_identity = ("test-provider", "test-model", "current-model-fingerprint")
    monkeypatch.setattr(
        rag, "get_embedding_index_identity", lambda: current_identity
    )
    monkeypatch.setattr(
        rag,
        "embed_documents_sync",
        lambda texts: [[0.25] * 768 for _ in texts],
    )

    file.extracted_text = "Updated source text with the latest verified details."
    db_session.flush()
    expected_text_fingerprint = extracted_text_fingerprint(file.extracted_text)

    count = rag.index_file_chunks(db_session, file)
    db_session.commit()
    db_session.refresh(file)

    chunks = (
        db_session.query(FileChunk)
        .filter(FileChunk.file_id == file.id)
        .order_by(FileChunk.chunk_index.asc())
        .all()
    )
    assert count == len(chunks) == 1
    assert chunks[0].content == "Updated source text with the latest verified details."
    assert file.extracted_text_sha256 == expected_text_fingerprint
    assert file.indexed_text_sha256 == expected_text_fingerprint
    assert file.indexed_embedding_fingerprint == current_identity[2]
    assert file.indexed_embedding_provider == current_identity[0]
    assert file.indexed_embedding_model == current_identity[1]
    assert file.indexed_at is not None


def test_failed_reindex_preserves_rows_but_marks_old_index_stale(
    db_session, monkeypatch
):
    """A provider failure never deletes old chunks, but changed text invalidates them."""
    from app.services.embeddings import EmbeddingServiceError

    user = User(email="rag-reindex-failure@example.com", hashed_password="hashed")
    db_session.add(user)
    db_session.flush()

    workspace = Workspace(owner_id=user.id, name="Reindex failure")
    db_session.add(workspace)
    db_session.flush()

    file = FileAttachment(
        user_id=user.id,
        workspace_id=workspace.id,
        project_id=None,
        original_filename="notes.txt",
        stored_filename="rag-reindex-failure.txt",
        content_type="text/plain",
        size_bytes=64,
        extracted_text="Previous source text.",
    )
    db_session.add(file)
    db_session.flush()

    previous_fingerprint = extracted_text_fingerprint(file.extracted_text)
    file.indexed_text_sha256 = previous_fingerprint
    file.indexed_embedding_fingerprint = "current-model-fingerprint"
    file.indexed_embedding_provider = "test-provider"
    file.indexed_embedding_model = "test-model"
    db_session.add(
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            content="Previous source text.",
            embedding=[0.1] * 768,
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        rag,
        "get_embedding_index_identity",
        lambda: ("test-provider", "test-model", "current-model-fingerprint"),
    )

    def fail_embedding(_texts):
        raise EmbeddingServiceError("provider unavailable")

    monkeypatch.setattr(rag, "embed_documents_sync", fail_embedding)
    file.extracted_text = "Updated source text that has not been indexed yet."
    db_session.flush()
    new_fingerprint = extracted_text_fingerprint(file.extracted_text)

    with pytest.raises(EmbeddingServiceError, match="provider unavailable"):
        rag.index_file_chunks(db_session, file)

    chunks = (
        db_session.query(FileChunk)
        .filter(FileChunk.file_id == file.id)
        .order_by(FileChunk.chunk_index.asc())
        .all()
    )
    assert len(chunks) == 1
    assert chunks[0].content == "Previous source text."
    assert file.indexed_text_sha256 == previous_fingerprint
    assert file.extracted_text_sha256 == new_fingerprint
    assert file.indexed_text_sha256 != file.extracted_text_sha256


def test_empty_source_text_removes_stale_chunks_and_index_identity(
    db_session, monkeypatch
):
    """Clearing extracted text must invalidate the index and delete old chunks."""
    user = User(email="rag-empty-source@example.com", hashed_password="hashed")
    db_session.add(user)
    db_session.flush()

    workspace = Workspace(owner_id=user.id, name="Empty source invalidation")
    db_session.add(workspace)
    db_session.flush()

    file = FileAttachment(
        user_id=user.id,
        workspace_id=workspace.id,
        project_id=None,
        original_filename="notes.txt",
        stored_filename="rag-empty-source.txt",
        content_type="text/plain",
        size_bytes=32,
        extracted_text="Source text that was previously indexed.",
    )
    db_session.add(file)
    db_session.flush()

    source_fingerprint = extracted_text_fingerprint(file.extracted_text)
    file.indexed_text_sha256 = source_fingerprint
    file.indexed_embedding_fingerprint = "active-model-fingerprint"
    file.indexed_embedding_provider = "test-provider"
    file.indexed_embedding_model = "test-model"
    db_session.add(
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            content="Stale chunk from source text.",
            embedding=[0.1] * 768,
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        rag,
        "get_embedding_index_identity",
        lambda: ("test-provider", "test-model", "active-model-fingerprint"),
    )
    file.extracted_text = ""
    db_session.flush()

    assert rag.index_file_chunks(db_session, file) == 0
    db_session.commit()
    db_session.refresh(file)

    assert db_session.query(FileChunk).filter(FileChunk.file_id == file.id).count() == 0
    assert file.extracted_text_sha256 is None
    assert file.indexed_text_sha256 is None
    assert file.indexed_embedding_fingerprint is None
    assert file.indexed_embedding_provider is None
    assert file.indexed_embedding_model is None
    assert file.indexed_at is None
