"""Regression tests for file source and embedding index fingerprints."""

from datetime import datetime, timezone

import pytest

from app.models.file_attachment import FileAttachment, extracted_text_fingerprint
from app.models.file_chunk import FileChunk
from app.models.user import User
from app.services import embeddings, rag


def _create_indexed_file(db_session, *, email: str, filename: str, text: str):
    user = User(email=email, hashed_password="hashed")
    db_session.add(user)
    db_session.flush()
    file = FileAttachment(
        user_id=user.id,
        original_filename=filename,
        stored_filename=filename,
        content_type="text/plain",
        size_bytes=len(text),
        extracted_text=text,
    )
    db_session.add(file)
    db_session.flush()
    return file


def test_extracted_text_fingerprint_normalizes_whitespace():
    assert extracted_text_fingerprint("  Linux\n\t networking  ") == (
        extracted_text_fingerprint("Linux networking")
    )
    assert extracted_text_fingerprint(None) is None
    assert extracted_text_fingerprint(" \n\t ") is None


def test_successful_reindex_replaces_chunks_and_records_index_identity(
    db_session, monkeypatch
):
    file = _create_indexed_file(
        db_session,
        email="rag-index-fingerprint-success@example.com",
        filename="fingerprint-success.txt",
        text="Original text that will be replaced.",
    )
    db_session.add(
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            content="Old chunk content.",
            embedding=[0.1] * 768,
        )
    )
    db_session.commit()

    current_identity = (
        "test-provider",
        "test-model",
        "current-embedding-fingerprint",
    )
    monkeypatch.setattr(
        rag, "get_embedding_index_identity", lambda: current_identity
    )
    monkeypatch.setattr(
        rag,
        "embed_documents_sync",
        lambda texts: [[0.25] * 768 for _ in texts],
    )

    file.extracted_text = "Updated source text with current content."
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
    assert chunks[0].content == "Updated source text with current content."
    assert file.extracted_text_sha256 == expected_text_fingerprint
    assert file.indexed_text_sha256 == expected_text_fingerprint
    assert file.indexed_embedding_fingerprint == current_identity[2]
    assert file.indexed_embedding_provider == current_identity[0]
    assert file.indexed_embedding_model == current_identity[1]
    assert isinstance(file.indexed_at, datetime)
    assert file.indexed_at.tzinfo is not None


def test_failed_reindex_preserves_previous_chunks_and_index_metadata(
    db_session, monkeypatch
):
    file = _create_indexed_file(
        db_session,
        email="rag-index-fingerprint-failure@example.com",
        filename="fingerprint-failure.txt",
        text="Previous source text.",
    )
    previous_text_fingerprint = extracted_text_fingerprint(file.extracted_text)
    file.indexed_text_sha256 = previous_text_fingerprint
    file.indexed_embedding_fingerprint = "previous-embedding-fingerprint"
    file.indexed_embedding_provider = "test-provider"
    file.indexed_embedding_model = "previous-model"
    file.indexed_at = datetime.now(timezone.utc)
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
        lambda: ("test-provider", "current-model", "current-fingerprint"),
    )

    def fail_embedding(_texts):
        raise embeddings.EmbeddingServiceError("provider unavailable")

    monkeypatch.setattr(rag, "embed_documents_sync", fail_embedding)
    file.extracted_text = "New source text which has not been indexed."
    db_session.flush()
    current_text_fingerprint = extracted_text_fingerprint(file.extracted_text)

    with pytest.raises(embeddings.EmbeddingServiceError, match="provider unavailable"):
        rag.index_file_chunks(db_session, file)

    chunks = (
        db_session.query(FileChunk)
        .filter(FileChunk.file_id == file.id)
        .order_by(FileChunk.chunk_index.asc())
        .all()
    )
    assert len(chunks) == 1
    assert chunks[0].content == "Previous source text."
    assert file.indexed_text_sha256 == previous_text_fingerprint
    assert file.extracted_text_sha256 == current_text_fingerprint
    assert file.indexed_text_sha256 != file.extracted_text_sha256
    assert file.indexed_embedding_fingerprint == "previous-embedding-fingerprint"
    assert file.indexed_embedding_model == "previous-model"


def test_empty_source_removes_stale_chunks_and_clears_index_identity(db_session):
    file = _create_indexed_file(
        db_session,
        email="rag-index-fingerprint-empty@example.com",
        filename="fingerprint-empty.txt",
        text="Previously indexed source text.",
    )
    file.indexed_text_sha256 = extracted_text_fingerprint(file.extracted_text)
    file.indexed_embedding_fingerprint = "previous-embedding-fingerprint"
    file.indexed_embedding_provider = "test-provider"
    file.indexed_embedding_model = "test-model"
    file.indexed_at = datetime.now(timezone.utc)
    db_session.add(
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            content="Previously indexed source text.",
            embedding=[0.1] * 768,
        )
    )
    db_session.commit()

    file.extracted_text = " \n "
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
