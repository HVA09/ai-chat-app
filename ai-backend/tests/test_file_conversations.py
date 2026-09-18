"""اختبارات ربط الملفات بالمحادثات مع حماية الملكية."""
from unittest.mock import AsyncMock

from app.config import settings as app_settings
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_attach_and_detach_file_to_conversation(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "file-chat@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "ابدأ"},
        headers=headers,
    ).json()["conversation_id"]

    upload = client.post(
        "/files/upload",
        files={"file": ("note.csv", b"a,b\n1,2\n", "text/csv")},
        headers=headers,
    )
    file_id = upload.json()["id"]
    assert upload.json()["conversation_id"] is None

    attached = client.patch(
        f"/files/{file_id}/conversation",
        json={"conversation_id": conversation_id},
        headers=headers,
    )
    assert attached.status_code == 200
    assert attached.json()["conversation_id"] == conversation_id

    detached = client.patch(
        f"/files/{file_id}/conversation",
        json={"conversation_id": None},
        headers=headers,
    )
    assert detached.status_code == 200
    assert detached.json()["conversation_id"] is None


def test_cannot_attach_file_to_other_users_conversation(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "file-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "خاص"},
        headers=headers_a,
    ).json()["conversation_id"]

    upload = client.post(
        "/files/upload",
        files={"file": ("secret.csv", b"x,y\n1,2\n", "text/csv")},
        headers=headers_a,
    )
    file_id = upload.json()["id"]

    token_b = _register_and_login(client, "file-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = client.patch(
        f"/files/{file_id}/conversation",
        json={"conversation_id": conversation_id},
        headers=headers_b,
    )
    assert response.status_code == 404


def test_attached_file_is_cleared_when_conversation_is_deleted(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "file-delete@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة"},
        headers=headers,
    ).json()["conversation_id"]

    upload = client.post(
        "/files/upload",
        files={"file": ("data.csv", b"a,b\n1,2\n", "text/csv")},
        headers=headers,
    )
    file_id = upload.json()["id"]
    client.patch(
        f"/files/{file_id}/conversation",
        json={"conversation_id": conversation_id},
        headers=headers,
    )

    assert client.delete(f"/conversations/{conversation_id}", headers=headers).status_code == 204
    listed = client.get("/files", headers=headers).json()
    assert listed[0]["conversation_id"] is None
