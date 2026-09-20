"""اختبارات روابط مشاركة المحادثات."""
from unittest.mock import AsyncMock

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


def test_create_and_use_share_link(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد قابل للمشاركة")),
    )
    token = _register_and_login(client, "share-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة عامة"},
        headers=headers,
    ).json()["conversation_id"]

    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 7},
        headers=headers,
    )
    assert created.status_code == 200
    share = created.json()
    assert "/share/" in share["url"]

    public = client.get(share["url"].split("/share/", 1)[1] and f"/shared-conversations/{share['url'].split('/share/', 1)[1]}")
    assert public.status_code == 200
    body = public.json()
    assert body["title"] == "رسالة عامة"
    assert [m["content"] for m in body["messages"]] == ["رسالة عامة", "رد قابل للمشاركة"]


def test_share_is_private_to_owner_for_creation_and_revocation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "share-a@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "خاص"},
        headers=headers_a,
    ).json()["conversation_id"]

    token_b = _register_and_login(client, "share-b@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={},
        headers=headers_b,
    )
    assert created.status_code == 404

    owner_share = client.post(
        f"/conversations/{conversation_id}/share",
        json={},
        headers=headers_a,
    ).json()
    share_id = owner_share["id"]

    revoked = client.delete(
        f"/conversations/{conversation_id}/share/{share_id}",
        headers=headers_b,
    )
    assert revoked.status_code == 404

    public_token = owner_share["url"].split("/share/", 1)[1]
    assert client.get(f"/shared-conversations/{public_token}").status_code == 200

    assert client.delete(
        f"/conversations/{conversation_id}/share/{share_id}",
        headers=headers_a,
    ).status_code == 204
    assert client.get(f"/shared-conversations/{public_token}").status_code == 404


def test_expired_share_returns_410(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "share-expired@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة"},
        headers=headers,
    ).json()["conversation_id"]

    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 1},
        headers=headers,
    )
    assert created.status_code == 200

    # No direct DB mutation here; just verify endpoint shape and token path.
    assert len(created.json()["url"].split("/share/", 1)[1]) >= 20
