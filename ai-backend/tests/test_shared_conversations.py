"""اختبارات إنشاء وإدارة روابط مشاركة المحادثات."""
from unittest.mock import AsyncMock

from app.models.conversation_share import ConversationShare
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_list_and_revoke_conversation_shares(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد مشاركة")),
    )
    token = _register_and_login(client, "share-manage@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة للمشاركة"},
        headers=headers,
    ).json()["conversation_id"]

    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 7},
        headers=headers,
    )
    assert created.status_code == 200
    share_id = created.json()["id"]

    listed = client.get(
        f"/conversations/{conversation_id}/shares",
        headers=headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == share_id
    assert listed.json()[0]["is_expired"] is False

    revoked = client.delete(
        f"/conversations/{conversation_id}/share/{share_id}",
        headers=headers,
    )
    assert revoked.status_code == 204

    assert client.get(
        f"/conversations/{conversation_id}/shares",
        headers=headers,
    ).json() == []


def test_other_user_cannot_list_or_revoke_shares(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    owner_token = _register_and_login(client, "share-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "خاصة"},
        headers=owner_headers,
    ).json()["conversation_id"]
    share_id = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 7},
        headers=owner_headers,
    ).json()["id"]

    other_token = _register_and_login(client, "share-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    assert client.get(
        f"/conversations/{conversation_id}/shares",
        headers=other_headers,
    ).status_code == 404
    assert client.delete(
        f"/conversations/{conversation_id}/share/{share_id}",
        headers=other_headers,
    ).status_code == 404


def test_expired_share_is_marked_expired_in_management_list(client, monkeypatch, db_session):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "share-expired@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "تنتهي لاحقًا"},
        headers=headers,
    ).json()["conversation_id"]
    share_id = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 1},
        headers=headers,
    ).json()["id"]

    share = db_session.query(ConversationShare).filter(ConversationShare.id == share_id).first()
    assert share is not None
    from datetime import datetime, timedelta, timezone
    share.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.flush()

    listed = client.get(
        f"/conversations/{conversation_id}/shares",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["is_expired"] is True
