"""Regression tests for bounded public conversation shares."""
from unittest.mock import AsyncMock

from app.models.conversation import Message, MessageRole
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email):
    client.post("/auth/register", json={"email": email, "password": "StrongPass123"})
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_public_share_bounds_history_and_projects_source_metadata(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="initial reply")),
    )
    token = _register_and_login(client, "share-bounds@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "initial message"},
        headers=headers,
    ).json()["conversation_id"]

    db_session.add_all(
        [
            Message(
                conversation_id=conversation_id,
                role=MessageRole.user,
                content=f"bounded-message-{index}",
                sources=[
                    {
                        "id": f"S{index}",
                        "filename": "source.txt",
                        "file_id": 987654,
                        "url": "javascript:alert(1)",
                        "snippet": "safe preview",
                        "internal_debug": "must not be exposed",
                    }
                ],
            )
            for index in range(101)
        ]
    )
    db_session.commit()

    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 7},
        headers=headers,
    )
    assert created.status_code == 200
    public_token = created.json()["url"].split("/share/", 1)[1]

    response = client.get(f"/shared-conversations/{public_token}")
    assert response.status_code == 200
    body = response.json()

    assert len(body["messages"]) == 100
    assert body["truncated"] is True
    assert body["messages"][-1]["content"] == "bounded-message-100"
    source = body["messages"][-1]["sources"][0]
    assert source["filename"] == "source.txt"
    assert source["snippet"] == "safe preview"
    assert "file_id" not in source
    assert "url" not in source
    assert "internal_debug" not in source


def test_public_share_caps_aggregate_and_per_message_content(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="initial reply")),
    )
    token = _register_and_login(client, "share-content-bounds@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "initial message"},
        headers=headers,
    ).json()["conversation_id"]

    db_session.add_all(
        [
            Message(
                conversation_id=conversation_id,
                role=MessageRole.user,
                content=(str(index) * 20_000),
            )
            for index in range(6)
        ]
    )
    db_session.commit()

    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 7},
        headers=headers,
    )
    public_token = created.json()["url"].split("/share/", 1)[1]
    response = client.get(f"/shared-conversations/{public_token}")

    assert response.status_code == 200
    body = response.json()
    assert body["truncated"] is True
    assert sum(len(message["content"]) for message in body["messages"]) <= 100_000
    assert all(len(message["content"]) <= 20_000 for message in body["messages"])
    assert body["messages"][-1]["content"] == "5" * 20_000
