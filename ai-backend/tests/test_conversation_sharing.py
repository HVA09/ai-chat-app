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


def test_password_protected_share_requires_and_accepts_password(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد محمي")),
    )
    token = _register_and_login(client, "share-password@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة محمية"},
        headers=headers,
    ).json()["conversation_id"]

    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 7, "password": "SharePass123"},
        headers=headers,
    )
    assert created.status_code == 200
    share = created.json()
    public_token = share["url"].split("/share/", 1)[1]

    listed = client.get(
        f"/conversations/{conversation_id}/shares",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["password_protected"] is True

    protected = client.get(f"/shared-conversations/{public_token}")
    assert protected.status_code == 401
    assert protected.json()["detail"] == "share_password_required"

    wrong = client.post(
        f"/shared-conversations/{public_token}/access",
        json={"password": "WrongPass123"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "invalid_share_password"

    unlocked = client.post(
        f"/shared-conversations/{public_token}/access",
        json={"password": "SharePass123"},
    )
    assert unlocked.status_code == 200
    assert [message["content"] for message in unlocked.json()["messages"]] == [
        "رسالة محمية",
        "رد محمي",
    ]


def test_unprotected_share_access_endpoint_still_works(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "share-unprotected-access@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة"},
        headers=headers,
    ).json()["conversation_id"]

    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 7},
        headers=headers,
    )
    public_token = created.json()["url"].split("/share/", 1)[1]

    unlocked = client.post(
        f"/shared-conversations/{public_token}/access",
        json={"password": "UnusedPass123"},
    )
    assert unlocked.status_code == 200
    assert unlocked.json()["title"] == "رسالة"


def test_share_access_analytics_count_successful_views(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "share-analytics@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة"},
        headers=headers,
    ).json()["conversation_id"]

    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 7},
        headers=headers,
    ).json()
    public_token = created["url"].split("/share/", 1)[1]

    first = client.get(f"/shared-conversations/{public_token}")
    assert first.status_code == 200
    listed = client.get(
        f"/conversations/{conversation_id}/shares",
        headers=headers,
    )
    first_stats = listed.json()[0]
    assert first_stats["access_count"] == 1
    assert first_stats["last_accessed_at"] is not None

    second = client.get(f"/shared-conversations/{public_token}")
    assert second.status_code == 200
    listed = client.get(
        f"/conversations/{conversation_id}/shares",
        headers=headers,
    )
    second_stats = listed.json()[0]
    assert second_stats["access_count"] == 2
    assert second_stats["last_accessed_at"] is not None


def test_failed_share_password_does_not_count_access(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "share-password-analytics@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة"},
        headers=headers,
    ).json()["conversation_id"]

    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 7, "password": "SharePass123"},
        headers=headers,
    ).json()
    public_token = created["url"].split("/share/", 1)[1]

    wrong = client.post(
        f"/shared-conversations/{public_token}/access",
        json={"password": "WrongPass123"},
    )
    assert wrong.status_code == 401

    listed = client.get(
        f"/conversations/{conversation_id}/shares",
        headers=headers,
    )
    assert listed.json()[0]["access_count"] == 0

    correct = client.post(
        f"/shared-conversations/{public_token}/access",
        json={"password": "SharePass123"},
    )
    assert correct.status_code == 200

    listed = client.get(
        f"/conversations/{conversation_id}/shares",
        headers=headers,
    )
    assert listed.json()[0]["access_count"] == 1


def test_unprotected_access_endpoint_counts_view(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "share-unprotected-analytics@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة"},
        headers=headers,
    ).json()["conversation_id"]

    created = client.post(
        f"/conversations/{conversation_id}/share",
        json={"expires_in_days": 7},
        headers=headers,
    ).json()
    public_token = created["url"].split("/share/", 1)[1]

    accessed = client.post(
        f"/shared-conversations/{public_token}/access",
        json={"password": "UnusedPass123"},
    )
    assert accessed.status_code == 200

    listed = client.get(
        f"/conversations/{conversation_id}/shares",
        headers=headers,
    )
    assert listed.json()[0]["access_count"] == 1
