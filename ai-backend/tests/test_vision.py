"""اختبارات تحليل الصور المرفقة بالمحادثة."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes"


def _register_and_login(client, email="vision@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_analyze_attached_image(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_vision_reply",
        AsyncMock(return_value=AIReply(text="الصورة تحتوي على عنصر تجريبي.")),
    )

    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "ابدأ"},
        headers=headers,
    ).json()["conversation_id"]

    uploaded = client.post(
        "/files/upload",
        params={"conversation_id": conversation_id},
        files={"file": ("test.png", PNG_HEADER, "image/png")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]

    response = client.post(
        "/chat/vision",
        json={
            "conversation_id": conversation_id,
            "file_id": file_id,
            "message": "ماذا ترى في الصورة؟",
        },
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["reply"] == "الصورة تحتوي على عنصر تجريبي."

    vision_call = chat_router_module.get_ai_vision_reply.await_args
    assert vision_call.args[0] == "ماذا ترى في الصورة؟"
    assert vision_call.args[1].startswith("data:image/png;base64,")
    assert vision_call.args[2]


def test_analyze_image_requires_attachment_to_conversation(client):
    token = _register_and_login(client, "vision-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "ابدأ"},
        headers=headers,
    ).json()["conversation_id"]

    uploaded = client.post(
        "/files/upload",
        files={"file": ("test.png", PNG_HEADER, "image/png")},
        headers=headers,
    )
    assert uploaded.status_code == 201

    response = client.post(
        "/chat/vision",
        json={
            "conversation_id": conversation_id,
            "file_id": uploaded.json()["id"],
            "message": "حللها",
        },
        headers=headers,
    )
    assert response.status_code == 404


def test_analyze_image_requires_authentication(client):
    response = client.post(
        "/chat/vision",
        json={"conversation_id": 1, "file_id": 1, "message": "حلل الصورة"},
    )
    assert response.status_code == 401
