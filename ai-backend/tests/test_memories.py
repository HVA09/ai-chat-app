"""اختبارات الذاكرة الدائمة للمستخدم."""
import json
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.routers import memories as memories_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email, password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return client.cookies.get("access_token")


def test_memory_crud_and_user_scoping(client):
    token = _register_and_login(client, "memory-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/memories",
        json={"content": "أفضل الإجابات المختصرة مع أمثلة عملية."},
        headers=headers,
    )
    assert created.status_code == 201
    memory = created.json()
    assert memory["content"].startswith("أفضل الإجابات")

    updated = client.patch(
        f"/memories/{memory['id']}",
        json={"content": "أفضل الشرح بالعربية مع أمثلة عملية."},
        headers=headers,
    )
    assert updated.status_code == 200
    assert "بالعربية" in updated.json()["content"]

    listed = client.get("/memories", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == memory["id"]

    other = _register_and_login(client, "memory-other@example.com")
    other_headers = {"Authorization": f"Bearer {other}"}
    assert client.patch(
        f"/memories/{memory['id']}",
        json={"content": "اختراق"},
        headers=other_headers,
    ).status_code == 404
    assert client.delete(
        f"/memories/{memory['id']}",
        headers=other_headers,
    ).status_code == 404

    assert client.delete(f"/memories/{memory['id']}", headers=headers).status_code == 204
    assert client.get("/memories", headers=headers).json() == []


def test_memory_rejects_blank_content(client):
    token = _register_and_login(client, "memory-validation@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/memories",
        json={"content": "   "},
        headers=headers,
    )
    assert response.status_code == 422



def test_suggest_memories_returns_reviewable_candidates_without_saving(
    client, monkeypatch
):
    mock_reply = AsyncMock(
        return_value=AIReply(
            text=json.dumps(
                {
                    "suggestions": [
                        {
                            "content": "يفضل الشرح بالعربية مع أمثلة عملية.",
                            "evidence": "أفضل الشرح بالعربية مع أمثلة عملية.",
                        },
                        {
                            "content": "تفضيل غير مدعوم",
                            "evidence": "لم يذكر المستخدم هذا الشيء.",
                        },
                        {
                            "content": "API key: abcdefghijklmnop",
                            "evidence": "أفضل الشرح بالعربية مع أمثلة عملية.",
                        },
                    ]
                },
                ensure_ascii=False,
            ),
            input_tokens=120,
            output_tokens=40,
            provider="test-provider",
            latency_ms=15,
        )
    )
    monkeypatch.setattr(
        memories_router_module, "get_ai_reply", mock_reply
    )
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تجريبي")),
    )

    token = _register_and_login(client, "memory-suggestions@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    chat = client.post(
        "/chat",
        json={"message": "أفضل الشرح بالعربية مع أمثلة عملية."},
        headers=headers,
    )
    assert chat.status_code == 200
    conversation_id = chat.json()["conversation_id"]

    response = client.post(
        "/memories/suggest",
        json={"conversation_id": conversation_id},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] == conversation_id
    assert body["suggestions"] == [
        {
            "content": "يفضل الشرح بالعربية مع أمثلة عملية.",
            "evidence": "أفضل الشرح بالعربية مع أمثلة عملية.",
        }
    ]
    assert client.get("/memories", headers=headers).json() == []


def test_suggest_memories_cannot_read_another_users_conversation(
    client, monkeypatch
):
    mock_reply = AsyncMock(return_value=AIReply(text='{"suggestions": []}'))
    monkeypatch.setattr(
        memories_router_module, "get_ai_reply", mock_reply
    )
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تجريبي")),
    )

    owner_token = _register_and_login(client, "memory-suggest-owner@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    chat = client.post(
        "/chat",
        json={"message": "هذه محادثة خاصة."},
        headers=owner_headers,
    )
    assert chat.status_code == 200
    conversation_id = chat.json()["conversation_id"]

    other_token = _register_and_login(client, "memory-suggest-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    response = client.post(
        "/memories/suggest",
        json={"conversation_id": conversation_id},
        headers=other_headers,
    )

    assert response.status_code == 404
    mock_reply.assert_not_awaited()


def test_memory_suggestion_parser_rejects_duplicates_and_unverified_quotes():
    import pytest
    from fastapi import HTTPException
    from app.routers.memories import _parse_memory_suggestions

    parsed = _parse_memory_suggestions(
        json.dumps(
            {
                "suggestions": [
                    {
                        "content": "يفضل الشرح بالعربية.",
                        "evidence": "أشرح لي بالعربية.",
                    },
                    {
                        "content": "يفضل الشرح بالعربية.",
                        "evidence": "أشرح لي بالعربية.",
                    },
                    {
                        "content": "معلومة غير مدعومة.",
                        "evidence": "أنا أحب الاختراعات.",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        user_messages=["أشرح لي بالعربية."],
        existing_contents=set(),
    )
    assert [item.content for item in parsed] == ["يفضل الشرح بالعربية."]

    with pytest.raises(HTTPException) as error:
        _parse_memory_suggestions(
            "not json",
            user_messages=["أشرح لي بالعربية."],
            existing_contents=set(),
        )
    assert error.value.status_code == 502

def test_memory_suggestion_parser_rejects_sensitive_personal_facts():
    from app.routers.memories import _parse_memory_suggestions

    parsed = _parse_memory_suggestions(
        json.dumps(
            {
                "suggestions": [
                    {
                        "content": "يعاني المستخدم من مرض السكري.",
                        "evidence": "أعاني من مرض السكري.",
                    },
                    {
                        "content": "المستخدم مسلم.",
                        "evidence": "أنا مسلم.",
                    },
                    {
                        "content": "يستخدم المستخدم دواءً للضغط.",
                        "evidence": "أستخدم دواء الضغط يوميًا.",
                    },
                    {
                        "content": "يفضل الشرح بالعربية.",
                        "evidence": "أفضل الشرح بالعربية.",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        user_messages=[
            "أعاني من مرض السكري.",
            "أنا مسلم.",
            "أستخدم دواء الضغط يوميًا.",
            "أفضل الشرح بالعربية.",
        ],
        existing_contents=set(),
    )

    assert [item.content for item in parsed] == ["يفضل الشرح بالعربية."]


def test_memory_suggestion_parser_rejects_unlabeled_credentials_and_tokens():
    from app.routers.memories import _parse_memory_suggestions

    candidates = [
        {
            "content": "يجب إبقاء مفتاح خدمة الذكاء الاصطناعي خاصًا.",
            "evidence": "AIzaSyA1234567890abcdefghijklmnopqrstuv",
        },
        {
            "content": "يستخدم المستخدم رمز وصول خاصًا.",
            "evidence": "ghp_" + "A" * 30,
        },
        {
            "content": "يستخدم المستخدم مفتاح وصول للنشر.",
            "evidence": "AKIAIOSFODNN7EXAMPLE",
        },
        {
            "content": "يستخدم المستخدم رمز جلسة مؤقتًا.",
            "evidence": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.signatureSignatureMoreHere",
        },
        {
            "content": "يستخدم المستخدم اتصال قاعدة بيانات خاصًا.",
            "evidence": "postgresql://app_user:fake-pass-123@db.example.test:5432/app",
        },
        {
            "content": "يفضل الشرح بالعربية مع أمثلة.",
            "evidence": "أفضل الشرح بالعربية مع أمثلة عملية.",
        },
    ]
    user_messages = [item["evidence"] for item in candidates]

    parsed = _parse_memory_suggestions(
        json.dumps({"suggestions": candidates}, ensure_ascii=False),
        user_messages=user_messages,
        existing_contents=set(),
    )

    assert [item.content for item in parsed] == [
        "يفضل الشرح بالعربية مع أمثلة."
    ]


def test_memory_suggestion_sensitive_filter_covers_additional_raw_credentials():
    from app.routers.memories import _contains_sensitive_memory_data

    raw_credentials = [
        "sk_live_" + "A" * 24,
        "rk_test_" + "B" * 24,
        "xoxb-" + "1234567890-abcdefghijkl",
        "npm_" + "C" * 30,
        "pypi-" + "D" * 35,
        "glpat-" + "E" * 25,
        "github_pat_" + "G" * 35,
        "ya29." + "F" * 30,
        "AKIAIOSFODNN7EXAMPLE",
        "ASIAABCDEFGHIJKLMNOP",
        "postgresql+psycopg://app_user:fake-pass-123@db.example.test:5432/app",
        "redis://:fake-cache-pass@cache.example.test:6379/0",
        "-----BEGIN PRIVATE KEY-----",
        "https://hooks.slack.com/services/T123456/B123456/abcdef123456",
    ]

    assert all(_contains_sensitive_memory_data(value) for value in raw_credentials)
    assert not _contains_sensitive_memory_data(
        "أفضل الشرح بالعربية مع أمثلة عملية."
    )
