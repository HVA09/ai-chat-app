"""اختبارات فهرسة الصور للبحث الدلالي في RAG."""
from unittest.mock import AsyncMock

from app.models.file_attachment import FileAttachment
from app.models.file_chunk import FileChunk
from app.services.ai_providers.base import AIReply
from app.routers import files as files_router
from app.services import image_rag


PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes"


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_index_image_for_rag_is_explicit_and_persists_usage(client, monkeypatch, db_session, tmp_path):
    token = _register_and_login(client, "image-index@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    upload_root = tmp_path / "uploads"
    monkeypatch.setattr(files_router.settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr(files_router, "index_file_chunks", lambda db, file: 0)

    uploaded = client.post(
        "/files/upload",
        files={"file": ("chart.png", PNG_HEADER, "image/png")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]
    assert uploaded.json()["is_ai_indexed"] is False

    monkeypatch.setattr(
        image_rag,
        "get_ai_vision_reply",
        AsyncMock(
            return_value=AIReply(
                text="مخطط مبيعات يظهر ارتفاعًا في الربع الرابع.",
                input_tokens=10,
                output_tokens=20,
                provider="gemini",
                latency_ms=123,
            )
        ),
    )
    def fake_index_file_chunks(db, file):
        db.query(FileChunk).filter(FileChunk.file_id == file.id).delete(synchronize_session=False)
        db.add(
            FileChunk(
                file_id=file.id,
                chunk_index=0,
                content=file.extracted_text or "",
                embedding=[0.1] * 768,
            )
        )
        db.flush()
        return 1

    monkeypatch.setattr(image_rag, "index_file_chunks", fake_index_file_chunks)

    response = client.post(
        f"/files/{file_id}/index-image",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["is_ai_indexed"] is True

    attachment = db_session.get(FileAttachment, file_id)
    assert "[IMAGE DESCRIPTION]" in attachment.extracted_text

    # المستخدم ليس admin، لذا نفحص سجل الاستخدام مباشرة في قاعدة الاختبار.
    from app.models.usage_log import UsageLog

    logs = (
        db_session.query(UsageLog)
        .filter(UsageLog.user_id == attachment.user_id, UsageLog.endpoint == "/files/index-image")
        .all()
    )
    assert len(logs) == 1
    assert logs[0].provider == "gemini"
    assert logs[0].input_tokens == 10
    assert logs[0].output_tokens == 20


def test_index_image_for_rag_rejects_non_image(client, monkeypatch):
    token = _register_and_login(client, "not-image@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(files_router, "index_file_chunks", lambda db, file: 0)

    uploaded = client.post(
        "/files/upload",
        files={"file": ("note.txt", b"hello world", "text/plain")},
        headers=headers,
    )
    assert uploaded.status_code == 201

    response = client.post(
        f"/files/{uploaded.json()['id']}/index-image",
        headers=headers,
    )
    assert response.status_code == 400
