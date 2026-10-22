"""اختبارات ربط الملفات بالمحادثات."""
from unittest.mock import AsyncMock

from app.config import settings as app_settings
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def _make_png():
    return b"\x89PNG\r\n\x1a\n" + b"fake"


def _make_chat(client, headers, monkeypatch, text="رسالة"):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تجريبي")),
    )
    response = client.post("/chat", json={"message": text}, headers=headers)
    assert response.status_code == 200
    return response.json()["conversation_id"]


def _upload(client, headers, filename="note.png", content=None, conversation_id=None):
    content = content or _make_png()
    params = {}
    if conversation_id is not None:
        params["conversation_id"] = conversation_id
    response = client.post(
        "/files/upload",
        params=params,
        files={"file": (filename, content, "image/png")},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_upload_attaches_file_to_owned_conversation(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client, "link-upload@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = _make_chat(client, headers, monkeypatch)

    uploaded = _upload(client, headers, conversation_id=conversation_id)
    assert uploaded["is_attached"] is True

    current = client.get(
        "/files",
        params={"conversation_id": conversation_id},
        headers=headers,
    )
    assert current.status_code == 200
    assert [item["id"] for item in current.json()] == [uploaded["id"]]


def test_attach_and_detach_existing_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client, "link-existing@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = _make_chat(client, headers, monkeypatch)
    uploaded = _upload(client, headers)

    attached = client.post(
        f"/files/{uploaded['id']}/attach/{conversation_id}",
        headers=headers,
    )
    assert attached.status_code == 200
    assert attached.json()["is_attached"] is True

    all_files = client.get(
        "/files",
        params={"conversation_id": conversation_id, "include_unattached": True},
        headers=headers,
    )
    assert all_files.status_code == 200
    assert all_files.json()[0]["is_attached"] is True

    detached = client.delete(
        f"/files/{uploaded['id']}/attach/{conversation_id}",
        headers=headers,
    )
    assert detached.status_code == 204

    after = client.get(
        "/files",
        params={"conversation_id": conversation_id},
        headers=headers,
    )
    assert after.status_code == 200
    assert after.json() == []


def test_cannot_attach_to_other_users_conversation(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token_a = _register_and_login(client, "link-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    uploaded = _upload(client, headers_a)

    token_b = _register_and_login(client, "link-intruder@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    conversation_id = _make_chat(client, headers_b, monkeypatch)

    response = client.post(
        f"/files/{uploaded['id']}/attach/{conversation_id}",
        headers=headers_b,
    )
    assert response.status_code == 404


def test_conversation_delete_removes_file_link_but_not_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client, "link-delete@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = _make_chat(client, headers, monkeypatch)
    uploaded = _upload(client, headers, conversation_id=conversation_id)

    delete_conversation = client.delete(
        f"/conversations/{conversation_id}",
        headers=headers,
    )
    assert delete_conversation.status_code == 204

    remaining = client.get(
        f"/files/{uploaded['id']}",
        headers=headers,
    )
    assert remaining.status_code == 200


def test_uploaded_text_file_flows_through_download_and_chat_context(
    client, tmp_path, monkeypatch
):
    """Exercise one real API flow from upload through retrieval as chat context."""
    from app.routers import files as files_router

    mock_reply = AsyncMock(return_value=AIReply(text="تم تحليل الملف"))
    monkeypatch.setattr(chat_router_module, "get_ai_reply", mock_reply)
    monkeypatch.setattr(files_router, "index_file_chunks", lambda *_args, **_kwargs: 0)

    async def no_semantic_results(*_args, **_kwargs):
        return []

    monkeypatch.setattr(
        chat_router_module,
        "retrieve_relevant_chunks",
        no_semantic_results,
    )
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))

    token = _register_and_login(client, "upload-chat-roundtrip@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    started = client.post(
        "/chat",
        json={"message": "ابدأ اختبار تكامل الملفات"},
        headers=headers,
    )
    assert started.status_code == 200
    conversation_id = started.json()["conversation_id"]

    original_bytes = (
        "Release note: ATTACHMENT_E2E_CODENAME=NEBULA-48\\n"
        "This marker must reach the assistant as untrusted file context.\\n"
    ).encode("utf-8")
    uploaded = client.post(
        "/files/upload",
        params={"conversation_id": conversation_id},
        files={"file": ("release-notes.txt", original_bytes, "text/plain")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    file_payload = uploaded.json()
    assert file_payload["is_attached"] is True
    assert file_payload["content_type"] == "text/plain"

    listed = client.get(
        "/files",
        params={"conversation_id": conversation_id},
        headers=headers,
    )
    assert listed.status_code == 200
    assert any(item["id"] == file_payload["id"] for item in listed.json())

    downloaded = client.get(f"/files/{file_payload['id']}", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == original_bytes

    chat_response = client.post(
        "/chat",
        json={
            "message": "ما رمز الإطلاق الموجود في ملف الملاحظات المرفق؟",
            "conversation_id": conversation_id,
        },
        headers=headers,
    )
    assert chat_response.status_code == 200

    prompt = mock_reply.await_args.args[0]
    assert "[SOURCE S1: release-notes.txt]" in prompt
    assert "untrusted reference material" in prompt
    assert "ATTACHMENT_E2E_CODENAME=NEBULA-48" in prompt
