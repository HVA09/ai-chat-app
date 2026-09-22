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
