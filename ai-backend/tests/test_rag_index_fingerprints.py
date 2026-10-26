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
