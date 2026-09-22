"""اختبارات إلغاء بث المحادثة عند انقطاع اتصال العميل."""

import asyncio

from app.models.conversation import Conversation, Message, MessageRole
from app.models.user import User
from app.routers import chat as chat_router_module


class DisconnectingRequest:
    def __init__(self):
        self.calls = 0

    async def is_disconnected(self):
        self.calls += 1
        return self.calls >= 2


async def fake_stream(*args, **kwargs):
    yield "first"
    yield "second"


def test_stream_stops_and_does_not_persist_partial_response(client, db_session, monkeypatch):
    client.post(
        "/auth/register",
        json={"email": "disconnect@example.com", "password": "StrongPass123"},
    )
    login = client.post(
        "/auth/login",
        json={"email": "disconnect@example.com", "password": "StrongPass123"},
    )
    assert login.status_code == 200

    user = db_session.query(User).filter_by(email="disconnect@example.com").one()

    monkeypatch.setattr(chat_router_module, "stream_ai_reply", fake_stream)

    async def run():
        response = await chat_router_module.chat_stream(
            payload=chat_router_module.ChatRequest(message="hello"),
            request=DisconnectingRequest(),
            current_user=user,
            db=db_session,
        )
        chunks = []
        async for item in response.body_iterator:
            chunks.append(item.decode() if isinstance(item, bytes) else item)
        return response, "".join(chunks)

    response, body = asyncio.run(run())

    assert response.media_type == "text/event-stream"
    assert "event: chunk\ndata: first" in body
    assert "event: chunk\ndata: second" not in body
    assert "event: done" not in body

    conversation = (
        db_session.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.id.desc())
        .first()
    )
    assert conversation is not None
    assistants = (
        db_session.query(Message)
        .filter(
            Message.conversation_id == conversation.id,
            Message.role == MessageRole.assistant,
        )
        .all()
    )
    assert assistants == []
