"""Regression tests for releasing DB read transactions before chat streaming."""

from unittest.mock import AsyncMock

from app.models.conversation import Message
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_create_conversation(client, email):
    client.post(
        "/auth/register",
        json={"email": email, "password": "StrongPass123"},
    )
    login = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login.status_code == 200
    token = client.cookies.get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/chat",
        json={"message": "Original question"},
        headers=headers,
    )
    assert first.status_code == 200, first.text
    return headers, first.json()["conversation_id"]


def _track_session_rollback(db_session, monkeypatch):
    rollback = db_session.rollback
    calls = []

    def tracked_rollback():
        calls.append(True)
        return rollback()

    monkeypatch.setattr(db_session, "rollback", tracked_rollback)
    return calls


def test_regenerate_releases_read_transaction_before_ai_stream(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="Original answer")),
    )
    headers, conversation_id = _register_and_create_conversation(
        client, "stream-regenerate-release@example.com"
    )
    rollback_calls = _track_session_rollback(db_session, monkeypatch)

    async def fake_stream(*_args, **_kwargs):
        assert rollback_calls, "DB transaction must be released before AI streaming starts"
        yield "Regenerated answer"

    monkeypatch.setattr(chat_router_module, "stream_ai_reply", fake_stream)

    response = client.post(
        f"/chat/{conversation_id}/regenerate/stream",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert "event: done" in response.text
    messages = (
        db_session.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.asc())
        .all()
    )
    assert [message.content for message in messages] == [
        "Original question",
        "Regenerated answer",
    ]


def test_edit_releases_read_transaction_before_ai_stream(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="Original answer")),
    )
    headers, conversation_id = _register_and_create_conversation(
        client, "stream-edit-release@example.com"
    )
    rollback_calls = _track_session_rollback(db_session, monkeypatch)

    async def fake_stream(*_args, **_kwargs):
        assert rollback_calls, "DB transaction must be released before AI streaming starts"
        yield "Edited answer"

    monkeypatch.setattr(chat_router_module, "stream_ai_reply", fake_stream)

    response = client.post(
        f"/chat/{conversation_id}/edit/stream",
        json={"message_index": 1, "message": "Edited question"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert "event: done" in response.text
    messages = (
        db_session.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.asc())
        .all()
    )
    assert [message.content for message in messages] == [
        "Edited question",
        "Edited answer",
    ]
