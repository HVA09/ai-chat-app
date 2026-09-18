"""اختبارات فهرسة المقاطع واسترجاع RAG."""
from unittest.mock import AsyncMock

from app.models.file_attachment import FileAttachment
from app.models.file_chunk import FileChunk
from app.models.user import User
from app.routers import chat as chat_router_module
from app.services import rag


def _register_and_login(client, email):
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    response = client.post("/auth/login", json={"email": email, "password": "StrongPass123"})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_chunk_text_creates_overlapping_chunks():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = rag.chunk_text(text, chunk_size=120, overlap=20)
    assert len(chunks) > 3
    assert chunks[0][-15:] == chunks[1][:15]


def test_index_file_chunks_persists_embeddings(db_session, monkeypatch):
    user = User(
        email="rag-index@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    db_session.flush()

    file = FileAttachment(
        user_id=user.id,
        original_filename="notes.txt",
        stored_filename="notes.txt",
        content_type="text/plain",
        size_bytes=100,
        extracted_text=" ".join(f"information{i}" for i in range(400)),
    )
    db_session.add(file)
    db_session.flush()

    def fake_embed(texts):
        return [[0.1] * 768 for _ in texts]

    monkeypatch.setattr(rag, "embed_documents_sync", fake_embed)

    count = rag.index_file_chunks(db_session, file)
    db_session.commit()

    chunks = (
        db_session.query(FileChunk)
        .filter(FileChunk.file_id == file.id)
        .order_by(FileChunk.chunk_index.asc())
        .all()
    )
    assert count == len(chunks)
    assert count > 1
    assert len(chunks[0].embedding) == 768


def test_chat_uses_retrieved_rag_context(client, monkeypatch, db_session):
    token = _register_and_login(client, "rag-chat@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/chat", json={"message": "ابدأ محادثة"}, headers=headers)
    conversation_id = first.json()["conversation_id"]

    user = db_session.query(User).filter(User.email == "rag-chat@example.com").one()
    file = FileAttachment(
        user_id=user.id,
        original_filename="linux.txt",
        stored_filename="linux.txt",
        content_type="text/plain",
        size_bytes=50,
        extracted_text="Linux is an operating system.",
    )
    db_session.add(file)
    db_session.flush()
    db_session.add(
        FileChunk(
            file_id=file.id,
            chunk_index=0,
            content="Linux is an operating system used to run servers.",
            embedding=[0.1] * 768,
        )
    )
    db_session.commit()

    from app.models.conversation_file_link import ConversationFileLink

    db_session.add(
        ConversationFileLink(conversation_id=conversation_id, file_id=file.id)
    )
    db_session.commit()

    mock_reply = AsyncMock(return_value=type("Reply", (), {"text": "رد", "input_tokens": 1, "output_tokens": 1})())
    monkeypatch.setattr(chat_router_module, "get_ai_reply", mock_reply)
    monkeypatch.setattr(
        chat_router_module,
        "retrieve_relevant_chunks",
        AsyncMock(
            return_value=[
                (
                    db_session.query(FileChunk).filter(FileChunk.file_id == file.id).one(),
                    file,
                )
            ]
        ),
    )

    response = client.post(
        "/chat",
        json={"message": "ما هو لينكس؟", "conversation_id": conversation_id},
        headers=headers,
    )
    assert response.status_code == 200
    sent = mock_reply.await_args.args[0]
    assert "[SOURCE: linux.txt | CHUNK: 1]" in sent
    assert "Linux is an operating system used to run servers." in sent
