"""اختبارات تحليل الصور المرفقة بالمحادثة."""
import base64
from contextlib import contextmanager
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
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تمهيدي")),
    )
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

    events = []
    monkeypatch.setattr(
        chat_router_module,
        "commit_and_release_connection",
        lambda _db: events.append("release"),
    )
    vision_reply = AsyncMock(
        side_effect=lambda *_args, **_kwargs: (
            events.append("vision") or AIReply(text="الصورة تحتوي على عنصر تجريبي.")
        )
    )
    monkeypatch.setattr(chat_router_module, "get_ai_vision_reply", vision_reply)

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
    # Release once before object storage, then again after the live ACL recheck
    # and before waiting for the remote vision provider.
    assert events == ["release", "release", "vision"]

    vision_call = chat_router_module.get_ai_vision_reply.await_args
    assert vision_call.args[0] == "ماذا ترى في الصورة؟"
    assert vision_call.args[1].startswith("data:image/png;base64,")
    assert vision_call.args[2]


def test_analyze_image_requires_attachment_to_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تمهيدي")),
    )
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

def test_analyze_attached_image_works_without_local_upload_copy(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تمهيدي")),
    )
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_vision_reply",
        AsyncMock(return_value=AIReply(text="تحليل من التخزين الخارجي")),
    )

    token = _register_and_login(client, "vision-remote-storage@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "ابدأ"},
        headers=headers,
    ).json()["conversation_id"]

    uploaded = client.post(
        "/files/upload",
        params={"conversation_id": conversation_id},
        files={"file": ("remote.png", PNG_HEADER, "image/png")},
        headers=headers,
    )
    assert uploaded.status_code == 201

    materialized_remote_copy = tmp_path / "remote.png"
    materialized_remote_copy.write_bytes(PNG_HEADER)
    materialize_calls = []

    @contextmanager
    def fake_materialize(object_key, fallback_path):
        materialize_calls.append((object_key, fallback_path))
        # Simulate a Render redeploy: the ephemeral local copy no longer exists.
        fallback_path.unlink(missing_ok=True)
        yield materialized_remote_copy

    monkeypatch.setattr(chat_router_module, "materialize_file", fake_materialize)

    response = client.post(
        "/chat/vision",
        json={
            "conversation_id": conversation_id,
            "file_id": uploaded.json()["id"],
            "message": "حلل الصورة",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert len(materialize_calls) == 1
    assert materialize_calls[0][0].startswith("users/")
    vision_call = chat_router_module.get_ai_vision_reply.await_args
    assert vision_call.args[1] == (
        "data:image/png;base64," + base64.b64encode(PNG_HEADER).decode("ascii")
    )


def test_analyze_attached_image_discards_result_when_access_is_revoked(
    client, monkeypatch, db_session
):
    # The setup conversation must not depend on a live provider credential.
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تمهيدي")),
    )
    from app.models.conversation import Message
    from app.models.usage_log import UsageLog
    from app.models.user import User

    token = _register_and_login(client, "vision-revoked-access@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "ابدأ"},
        headers=headers,
    ).json()["conversation_id"]
    uploaded = client.post(
        "/files/upload",
        params={"conversation_id": conversation_id},
        files={"file": ("revoked.png", PNG_HEADER, "image/png")},
        headers=headers,
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]

    original_authorization_check = (
        chat_router_module._get_authorized_file_context_conversation
    )
    authorization_checks = []

    def revoke_during_provider_call(conversation, db):
        authorization_checks.append(conversation.id)
        if len(authorization_checks) == 3:
            raise chat_router_module.HTTPException(
                status_code=404,
                detail="مساحة العمل غير متاحة",
            )
        return original_authorization_check(conversation, db)

    monkeypatch.setattr(
        chat_router_module,
        "_get_authorized_file_context_conversation",
        revoke_during_provider_call,
    )
    monkeypatch.setattr(
        chat_router_module,
        "commit_and_release_connection",
        lambda _db: None,
    )
    vision_reply = AsyncMock(return_value=AIReply(text="نتيجة يجب عدم حفظها"))
    monkeypatch.setattr(chat_router_module, "get_ai_vision_reply", vision_reply)

    messages_before = (
        db_session.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .count()
    )
    response = client.post(
        "/chat/vision",
        json={
            "conversation_id": conversation_id,
            "file_id": file_id,
            "message": "حلل الصورة",
        },
        headers=headers,
    )

    assert response.status_code == 404
    assert vision_reply.await_count == 1
    assert len(authorization_checks) == 3
    assert (
        db_session.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .count()
        == messages_before
    )
    user = db_session.query(User).filter(
        User.email == "vision-revoked-access@example.com"
    ).one()
    assert (
        db_session.query(UsageLog)
        .filter(
            UsageLog.user_id == user.id,
            UsageLog.endpoint == "/chat/vision",
        )
        .count()
        == 0
    )
