"""اختبارات المساعدين المخصصين."""
from unittest.mock import AsyncMock

from app.models import Assistant
from app.routers import chat as chat_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_assistant_crud(client):
    token = _register_and_login(client, "assistant@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/assistants",
        json={
            "name": "Python Tutor",
            "description": "يساعدني في تعلم بايثون",
            "instructions": "اشرح بالعربية وبخطوات بسيطة، ثم أعطني تمرينًا.",
        },
        headers=headers,
    )
    assert created.status_code == 201
    assistant = created.json()
    assert assistant["name"] == "Python Tutor"

    listed = client.get("/assistants", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == assistant["id"]

    updated = client.patch(
        f"/assistants/{assistant['id']}",
        json={"name": "Python Coach"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Python Coach"

    deleted = client.delete(f"/assistants/{assistant['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get("/assistants", headers=headers).json() == []


def test_duplicate_assistant_name_rejected_case_insensitively(client):
    token = _register_and_login(client, "assistant-dup@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post(
        "/assistants",
        json={"name": "Tutor", "instructions": "Explain simply."},
        headers=headers,
    ).status_code == 201

    duplicate = client.post(
        "/assistants",
        json={"name": " tutor ", "instructions": "Explain simply."},
        headers=headers,
    )
    assert duplicate.status_code == 409


def test_assistant_is_private_to_owner(client):
    token_a = _register_and_login(client, "assistant-owner@example.com")
    assistant = client.post(
        "/assistants",
        json={"name": "Private", "instructions": "Private instructions."},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()

    token_b = _register_and_login(client, "assistant-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.get(f"/assistants", headers=headers_b).json() == []
    assert client.patch(
        f"/assistants/{assistant['id']}",
        json={"name": "Hijacked"},
        headers=headers_b,
    ).status_code == 404
    assert client.delete(
        f"/assistants/{assistant['id']}",
        headers=headers_b,
    ).status_code == 404


def test_chat_uses_assistant_instructions(client, monkeypatch):
    mock_reply = AsyncMock(return_value=AIReply(text="رد"))
    monkeypatch.setattr(chat_router_module, "get_ai_reply", mock_reply)

    token = _register_and_login(client, "assistant-chat@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assistant = client.post(
        "/assistants",
        json={
            "name": "Researcher",
            "instructions": "لخص الإجابة في 3 نقاط.",
        },
        headers=headers,
    ).json()

    response = client.post(
        "/chat",
        json={
            "message": "ما هو لينكس؟",
            "assistant_id": assistant["id"],
        },
        headers=headers,
    )
    assert response.status_code == 200

    sent_message = mock_reply.await_args.args[0]
    assert "[ASSISTANT INSTRUCTIONS]" in sent_message
    assert "لخص الإجابة في 3 نقاط." in sent_message

    conversation_id = response.json()["conversation_id"]
    detail = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert detail.json()["assistant_id"] == assistant["id"]


def test_assistant_version_history_and_restore(client):
    token = _register_and_login(client, "assistant-versions@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/assistants",
        json={
            "name": "Tutor",
            "description": "Original",
            "instructions": "اشرح بالعربية.",
        },
        headers=headers,
    )
    assert created.status_code == 201
    assistant = created.json()

    versions = client.get(
        f"/assistants/{assistant['id']}/versions",
        headers=headers,
    )
    assert versions.status_code == 200
    assert len(versions.json()) == 1
    assert versions.json()[0]["version"] == 1
    assert versions.json()[0]["instructions"] == "اشرح بالعربية."

    updated = client.patch(
        f"/assistants/{assistant['id']}",
        json={"instructions": "اشرح بالإنجليزية وبأمثلة عملية."},
        headers=headers,
    )
    assert updated.status_code == 200

    versions = client.get(
        f"/assistants/{assistant['id']}/versions",
        headers=headers,
    )
    assert [item["version"] for item in versions.json()] == [2, 1]

    restored = client.post(
        f"/assistants/{assistant['id']}/versions/1/restore",
        headers=headers,
    )
    assert restored.status_code == 200
    assert restored.json()["instructions"] == "اشرح بالعربية."

    versions = client.get(
        f"/assistants/{assistant['id']}/versions",
        headers=headers,
    )
    assert [item["version"] for item in versions.json()] == [3, 2, 1]
    assert versions.json()[0]["instructions"] == "اشرح بالعربية."


def test_assistant_version_compare_current(client):
    token = _register_and_login(client, "assistant-version-compare@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assistant = client.post(
        "/assistants",
        json={
            "name": "Tutor",
            "description": "Original",
            "instructions": "اشرح بالعربية.",
        },
        headers=headers,
    ).json()

    client.patch(
        f"/assistants/{assistant['id']}",
        json={
            "name": "Tutor Updated",
            "description": "Updated",
            "instructions": "اشرح بالإنجليزية وبأمثلة.",
        },
        headers=headers,
    )

    response = client.get(
        f"/assistants/{assistant['id']}/versions/1/compare-current",
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["from_version"] == 1
    assert payload["changed"] is True
    assert "-name: Tutor" in payload["diff"]
    assert "+name: Tutor Updated" in payload["diff"]
    assert "-اشرح بالعربية." in payload["diff"]
    assert "+اشرح بالإنجليزية وبأمثلة." in payload["diff"]

    assert client.get(
        f"/assistants/{assistant['id']}/versions/999/compare-current",
        headers=headers,
    ).status_code == 404


def test_assistant_versions_are_private_to_owner(client):
    token_a = _register_and_login(client, "assistant-version-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    assistant = client.post(
        "/assistants",
        json={"name": "Private", "instructions": "Secret instructions."},
        headers=headers_a,
    ).json()

    token_b = _register_and_login(client, "assistant-version-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    assert client.get(
        f"/assistants/{assistant['id']}/versions",
        headers=headers_b,
    ).status_code == 404
    assert client.post(
        f"/assistants/{assistant['id']}/versions/1/restore",
        headers=headers_b,
    ).status_code == 404


def test_assistant_usage_analytics(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "assistant-analytics@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    assistant = client.post(
        "/assistants",
        json={
            "name": "Analytics Tutor",
            "instructions": "اشرح بإيجاز.",
        },
        headers=headers,
    ).json()

    first = client.post(
        "/chat",
        json={"message": "رسالة 1", "assistant_id": assistant["id"]},
        headers=headers,
    )
    assert first.status_code == 200

    second = client.post(
        "/chat",
        json={
            "message": "رسالة 2",
            "conversation_id": first.json()["conversation_id"],
            "assistant_id": assistant["id"],
        },
        headers=headers,
    )
    assert second.status_code == 200

    analytics = client.get(
        f"/assistants/{assistant['id']}/analytics",
        params={"days": 30},
        headers=headers,
    )
    assert analytics.status_code == 200
    payload = analytics.json()
    assert payload["assistant_id"] == assistant["id"]
    assert payload["days"] == 30
    assert payload["conversation_count"] == 1
    assert payload["message_count"] == 4
    assert payload["active_user_count"] == 1
    assert payload["last_used_at"] is not None


def test_assistant_usage_analytics_is_private_to_owner(client):
    token_a = _register_and_login(client, "assistant-analytics-owner@example.com")
    assistant = client.post(
        "/assistants",
        json={"name": "Private Analytics", "instructions": "خاص"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()

    token_b = _register_and_login(client, "assistant-analytics-other@example.com")
    response = client.get(
        f"/assistants/{assistant['id']}/analytics",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_assistant_daily_usage_analytics(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "assistant-daily-analytics@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    assistant = client.post(
        "/assistants",
        json={"name": "Trend Assistant", "instructions": "اشرح باختصار."},
        headers=headers,
    ).json()

    response = client.post(
        "/chat",
        json={"message": "رسالة", "assistant_id": assistant["id"]},
        headers=headers,
    )
    assert response.status_code == 200

    trend = client.get(
        f"/assistants/{assistant['id']}/analytics/daily",
        params={"days": 7},
        headers=headers,
    )
    assert trend.status_code == 200
    payload = trend.json()
    assert len(payload) == 7
    assert payload[-1]["conversations"] == 1
    assert payload[-1]["messages"] == 2
    assert payload[-1]["active_users"] == 1


def test_assistant_daily_usage_analytics_is_private_to_owner(client):
    token_a = _register_and_login(client, "assistant-daily-owner@example.com")
    assistant = client.post(
        "/assistants",
        json={"name": "Private Trend", "instructions": "خاص"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()
    token_b = _register_and_login(client, "assistant-daily-other@example.com")
    response = client.get(
        f"/assistants/{assistant['id']}/analytics/daily",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404
