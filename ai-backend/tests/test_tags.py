"""اختبارات وسوم المحادثات وربطها بالمحادثات."""
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_tag_crud_and_duplicate_name(client):
    token = _register_and_login(client, "tag-crud@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/tags",
        json={"name": "Important", "color": "#FF0000"},
        headers=headers,
    )
    assert created.status_code == 201
    tag = created.json()
    assert tag["color"] == "#FF0000"

    duplicate = client.post(
        "/tags",
        json={"name": " important ", "color": "#00FF00"},
        headers=headers,
    )
    assert duplicate.status_code == 409

    renamed = client.patch(
        f"/tags/{tag['id']}",
        json={"name": "Urgent", "color": "#00AA00"},
        headers=headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Urgent"
    assert renamed.json()["color"] == "#00AA00"

    deleted = client.delete(f"/tags/{tag['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/tags", headers=headers).json() == []


def test_tags_are_user_scoped(client):
    token_a = _register_and_login(client, "tag-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    tag = client.post("/tags", json={"name": "Private"}, headers=headers_a).json()

    token_b = _register_and_login(client, "tag-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.patch(
        f"/tags/{tag['id']}",
        json={"name": "Hijacked"},
        headers=headers_b,
    ).status_code == 404
    assert client.delete(f"/tags/{tag['id']}", headers=headers_b).status_code == 404


def test_assign_multiple_tags_and_filter_conversations(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "tag-conversation@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    tag_a = client.post("/tags", json={"name": "Work", "color": "#FF0000"}, headers=headers).json()
    tag_b = client.post("/tags", json={"name": "Urgent", "color": "#00AA00"}, headers=headers).json()
    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة"},
        headers=headers,
    ).json()["conversation_id"]

    updated = client.put(
        f"/conversations/{conversation_id}/tags",
        json={"tag_ids": [tag_a["id"], tag_b["id"]]},
        headers=headers,
    )
    assert updated.status_code == 200
    assert {tag["id"] for tag in updated.json()["tags"]} == {tag_a["id"], tag_b["id"]}

    filtered = client.get(
        "/conversations",
        params={"tag_id": tag_b["id"]},
        headers=headers,
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [conversation_id]
    assert {tag["id"] for tag in filtered.json()[0]["tags"]} == {tag_a["id"], tag_b["id"]}

    cleared = client.put(
        f"/conversations/{conversation_id}/tags",
        json={"tag_ids": []},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["tags"] == []


def test_cannot_use_other_users_tag(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "tag-owner2@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    tag = client.post("/tags", json={"name": "Private"}, headers=headers_a).json()
    conversation_id = client.post(
        "/chat",
        json={"message": "خاص"},
        headers=headers_a,
    ).json()["conversation_id"]

    token_b = _register_and_login(client, "tag-other2@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    response = client.put(
        f"/conversations/{conversation_id}/tags",
        json={"tag_ids": [tag["id"]]},
        headers=headers_b,
    )
    assert response.status_code == 404
