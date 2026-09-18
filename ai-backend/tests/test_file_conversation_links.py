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


def _make_chat(client, headers, text="رسالة"):
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
    conversation_id = _make_chat(client, headers)

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
    conversation_id = _make_chat(client, headers)
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
    conversation_id = _make_chat(client, headers_b)

    response = client.post(
        f"/files/{uploaded['id']}/attach/{conversation_id}",
        headers=headers_b,
    )
    assert response.status_code == 404


def test_conversation_delete_removes_file_link_but_not_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    token = _register_and_login(client, "link-delete@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = _make_chat(client, headers)
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
