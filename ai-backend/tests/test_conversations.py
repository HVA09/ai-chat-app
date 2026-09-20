"""
اختبارات مسارات المحادثات: القائمة والتفاصيل والتصدير
"""
import json
from unittest.mock import AsyncMock

from app.routers import chat as chat_router_module
from app.routers import conversations as conversations_router_module
from app.services.ai_providers.base import AIReply


def _register_and_login(client, email="conv@example.com", password="StrongPass123"):
    client.post("/auth/register", json={"email": email, "password": password})
    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return client.cookies.get("access_token")


def test_list_conversations_empty(client):
    token = _register_and_login(client)
    response = client.get("/conversations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_list_conversations_supports_title_search(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "search@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/chat", json={"message": "بحث في تقرير المبيعات"}, headers=headers)
    second = client.post("/chat", json={"message": "محادثة السفر"}, headers=headers)

    first_id = first.json()["conversation_id"]
    second_id = second.json()["conversation_id"]

    client.patch(
        f"/conversations/{first_id}",
        json={"title": "تقرير المبيعات 2026"},
        headers=headers,
    )
    client.patch(
        f"/conversations/{second_id}",
        json={"title": "خطط السفر"},
        headers=headers,
    )

    response = client.get(
        "/conversations",
        params={"search": "المبيعات"},
        headers=headers,
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [first_id]


def test_list_conversations_searches_message_content(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="نتيجة فريدة للبحث")),
    )
    token = _register_and_login(client, "content-search@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/chat",
        json={"message": "رسالة عادية داخل المحادثة"},
        headers=headers,
    )
    conversation_id = created.json()["conversation_id"]

    no_match = client.get(
        "/conversations",
        params={"search": "كلمة_غير_موجودة"},
        headers=headers,
    )
    assert no_match.status_code == 200
    assert no_match.json() == []

    user_message_search = client.get(
        "/conversations",
        params={"search": "رسالة عادية"},
        headers=headers,
    )
    assert user_message_search.status_code == 200
    assert [item["id"] for item in user_message_search.json()] == [conversation_id]

    assistant_message_search = client.get(
        "/conversations",
        params={"search": "فريدة للبحث"},
        headers=headers,
    )
    assert assistant_message_search.status_code == 200
    assert [item["id"] for item in assistant_message_search.json()] == [conversation_id]


def test_list_conversations_sorts_by_last_activity(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "activity@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/chat",
        json={"message": "المحادثة الأولى"},
        headers=headers,
    )
    first_id = first.json()["conversation_id"]

    second = client.post(
        "/chat",
        json={"message": "المحادثة الثانية"},
        headers=headers,
    )
    second_id = second.json()["conversation_id"]

    response = client.get("/conversations", headers=headers)
    assert {item["id"] for item in response.json()} == {first_id, second_id}

    follow_up = client.post(
        "/chat",
        json={"message": "رسالة أحدث للمحادثة الأولى", "conversation_id": first_id},
        headers=headers,
    )
    assert follow_up.status_code == 200

    response = client.get("/conversations", headers=headers)
    assert [item["id"] for item in response.json()] == [first_id, second_id]
    assert response.json()[0]["updated_at"] >= response.json()[1]["updated_at"]


def test_list_and_get_conversation_after_chat(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد تجريبي")))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "أول رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]
    list_response = client.get("/conversations", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["id"] == conversation_id
    detail_response = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert detail_response.status_code == 200
    assert len(detail_response.json()["messages"]) == 2


def test_get_other_users_conversation_returns_404(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد تجريبي")))
    token_a = _register_and_login(client, "user_a@example.com")
    chat_response = client.post("/chat", json={"message": "سر خاص بالمستخدم أ"}, headers={"Authorization": f"Bearer {token_a}"})
    conversation_id = chat_response.json()["conversation_id"]
    token_b = _register_and_login(client, "user_b@example.com")
    response = client.get(f"/conversations/{conversation_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404


def test_conversations_require_authentication(client):
    response = client.get("/conversations")
    assert response.status_code == 401


def test_toggle_pin_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "pin@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]

    first = client.get("/conversations", headers=headers)
    assert first.json()[0]["is_pinned"] is False

    response = client.patch(f"/conversations/{conversation_id}/pin", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_pinned"] is True

    second = client.get("/conversations", headers=headers)
    assert second.json()[0]["is_pinned"] is True

    response = client.patch(f"/conversations/{conversation_id}/pin", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_pinned"] is False


def test_cannot_pin_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "pin-owner@example.com")
    chat_response = client.post(
        "/chat",
        json={"message": "خاص"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    conversation_id = chat_response.json()["conversation_id"]

    token_b = _register_and_login(client, "pin-other@example.com")
    response = client.patch(
        f"/conversations/{conversation_id}/pin",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_toggle_archive_conversation_and_filter(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "archive@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]

    response = client.patch(f"/conversations/{conversation_id}/archive", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_archived"] is True

    normal = client.get("/conversations", headers=headers)
    assert normal.json() == []

    archived = client.get(
        "/conversations",
        params={"include_archived": True},
        headers=headers,
    )
    assert len(archived.json()) == 1
    assert archived.json()[0]["is_archived"] is True

    response = client.patch(f"/conversations/{conversation_id}/archive", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_archived"] is False


def test_duplicate_conversation_copies_messages_and_metadata(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "duplicate@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    chat_response = client.post(
        "/chat",
        json={"message": "رسالة أصلية"},
        headers=headers,
    )
    original_id = chat_response.json()["conversation_id"]

    duplicate = client.post(
        f"/conversations/{original_id}/duplicate",
        headers=headers,
    )
    assert duplicate.status_code == 201
    payload = duplicate.json()

    assert payload["id"] != original_id
    assert payload["title"].startswith("نسخة من")
    assert payload["is_pinned"] is False
    assert payload["is_archived"] is False
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["content"] == "رسالة أصلية"
    assert payload["messages"][1]["content"] == "رد"

    original = client.get(
        f"/conversations/{original_id}",
        headers=headers,
    ).json()
    assert original["id"] == original_id
    assert [m["content"] for m in original["messages"]] == ["رسالة أصلية", "رد"]


def test_cannot_duplicate_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "duplicate-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    original_id = client.post(
        "/chat",
        json={"message": "خاص"},
        headers=headers_a,
    ).json()["conversation_id"]

    token_b = _register_and_login(client, "duplicate-other@example.com")
    response = client.post(
        f"/conversations/{original_id}/duplicate",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_toggle_message_bookmark_and_list_bookmarks(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد محفوظ")),
    )
    token = _register_and_login(client, "bookmark@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة مهمة للحفظ"},
        headers=headers,
    ).json()["conversation_id"]

    first = client.patch(
        f"/chat/{conversation_id}/messages/2/bookmark",
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json() == {"message_index": 2, "bookmarked": True}

    listed = client.get("/conversations/bookmarks", headers=headers)
    assert listed.status_code == 200
    payload = listed.json()
    assert len(payload) == 1
    assert payload[0]["conversation_id"] == conversation_id
    assert payload[0]["message_index"] == 2
    assert payload[0]["role"] == "assistant"
    assert payload[0]["content"] == "رد محفوظ"

    detail = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["messages"][1]["is_bookmarked"] is True

    second = client.patch(
        f"/chat/{conversation_id}/messages/2/bookmark",
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["bookmarked"] is False
    assert client.get("/conversations/bookmarks", headers=headers).json() == []


def test_cannot_bookmark_other_users_message(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "bookmark-owner@example.com")
    conversation_id = client.post(
        "/chat",
        json={"message": "خاص"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()["conversation_id"]

    token_b = _register_and_login(client, "bookmark-other@example.com")
    response = client.patch(
        f"/chat/{conversation_id}/messages/2/bookmark",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_rename_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]
    response = client.patch(f"/conversations/{conversation_id}", json={"title": "اسم جديد"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "اسم جديد"


def test_rename_rejects_blank_title(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]
    response = client.patch(f"/conversations/{conversation_id}", json={"title": "   "}, headers=headers)
    assert response.status_code == 422


def test_branch_conversation_copies_messages_up_to_selected_message(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد 1")),
    )
    token = _register_and_login(client, "branch@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "السؤال الأول"},
        headers=headers,
    ).json()["conversation_id"]

    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد 2")),
    )
    client.post(
        "/chat",
        json={"message": "السؤال الثاني", "conversation_id": conversation_id},
        headers=headers,
    )

    branch = client.post(
        f"/conversations/{conversation_id}/branch",
        params={"message_index": 2},
        headers=headers,
    )
    assert branch.status_code == 201
    payload = branch.json()
    assert payload["id"] != conversation_id
    assert payload["title"].startswith("فرع من")
    assert payload["is_pinned"] is False
    assert payload["is_archived"] is False
    assert payload["deleted_at"] is None
    assert len(payload["messages"]) == 2
    assert [item["content"] for item in payload["messages"]] == ["السؤال الأول", "رد 1"]
    assert payload["messages"][0]["is_bookmarked"] is False
    assert payload["messages"][1]["feedback"] is None
    assert payload["parent_conversation_id"] == conversation_id
    assert payload["branched_from_message_index"] == 2

    branches = client.get(
        f"/conversations/{conversation_id}/branches",
        headers=headers,
    )
    assert branches.status_code == 200
    assert [item["id"] for item in branches.json()] == [payload["id"]]


def test_branch_conversation_rejects_invalid_message_index(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "branch-invalid@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة"},
        headers=headers,
    ).json()["conversation_id"]

    low = client.post(
        f"/conversations/{conversation_id}/branch",
        params={"message_index": 0},
        headers=headers,
    )
    assert low.status_code == 422

    high = client.post(
        f"/conversations/{conversation_id}/branch",
        params={"message_index": 99},
        headers=headers,
    )
    assert high.status_code == 422


def test_cannot_branch_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "branch-owner@example.com")
    conversation_id = client.post(
        "/chat",
        json={"message": "خاص"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()["conversation_id"]

    token_b = _register_and_login(client, "branch-other@example.com")
    response = client.post(
        f"/conversations/{conversation_id}/branch",
        params={"message_index": 1},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_export_conversation_markdown(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تجريبي")),
    )
    token = _register_and_login(client, "export@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post(
        "/chat",
        json={"message": "أول رسالة للتصدير"},
        headers=headers,
    )
    conversation_id = chat_response.json()["conversation_id"]

    response = client.get(
        f"/conversations/{conversation_id}/export",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert response.text.startswith("# ")
    assert "Created: " in response.text
    assert "أول رسالة للتصدير" in response.text
    assert "رد تجريبي" in response.text


def test_export_conversation_json(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد JSON")),
    )
    token = _register_and_login(client, "export-json@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post(
        "/chat",
        json={"message": "بيانات JSON"},
        headers=headers,
    )
    conversation_id = chat_response.json()["conversation_id"]

    response = client.get(
        f"/conversations/{conversation_id}/export",
        params={"format": "json"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"].endswith(".json\"")

    payload = json.loads(response.text)
    assert payload["id"] == conversation_id
    assert payload["title"]
    assert payload["is_archived"] is False
    assert payload["folder_id"] is None
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "بيانات JSON"
    assert payload["messages"][1]["role"] == "assistant"
    assert payload["messages"][1]["content"] == "رد JSON"


def test_cannot_export_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "export-owner@example.com")
    chat_response = client.post(
        "/chat",
        json={"message": "خاص"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    conversation_id = chat_response.json()["conversation_id"]

    token_b = _register_and_login(client, "export-other@example.com")
    response = client.get(
        f"/conversations/{conversation_id}/export",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404



def test_trash_and_restore_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "trash@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "رسالة إلى السلة"},
        headers=headers,
    ).json()["conversation_id"]

    trashed = client.patch(
        f"/conversations/{conversation_id}/trash",
        headers=headers,
    )
    assert trashed.status_code == 200
    assert trashed.json()["deleted_at"] is not None

    normal = client.get("/conversations", headers=headers)
    assert normal.json() == []

    trash = client.get(
        "/conversations",
        params={"include_deleted": True},
        headers=headers,
    )
    assert len(trash.json()) == 1
    assert trash.json()[0]["id"] == conversation_id

    detail = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert detail.status_code == 404

    restored = client.patch(
        f"/conversations/{conversation_id}/trash",
        headers=headers,
    )
    assert restored.status_code == 200
    assert restored.json()["deleted_at"] is None
    assert len(client.get("/conversations", headers=headers).json()) == 1


def test_cannot_trash_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token_a = _register_and_login(client, "trash-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    conversation_id = client.post(
        "/chat",
        json={"message": "خاص"},
        headers=headers_a,
    ).json()["conversation_id"]

    token_b = _register_and_login(client, "trash-other@example.com")
    response = client.patch(
        f"/conversations/{conversation_id}/trash",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_delete_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}
    chat_response = client.post("/chat", json={"message": "رسالة"}, headers=headers)
    conversation_id = chat_response.json()["conversation_id"]
    delete_response = client.delete(f"/conversations/{conversation_id}", headers=headers)
    assert delete_response.status_code == 204
    assert client.get(f"/conversations/{conversation_id}", headers=headers).status_code == 404


def test_cannot_rename_or_delete_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(chat_router_module, "get_ai_reply", AsyncMock(return_value=AIReply(text="رد")))
    token_a = _register_and_login(client, "owner@example.com")
    chat_response = client.post("/chat", json={"message": "خاص بالمالك"}, headers={"Authorization": f"Bearer {token_a}"})
    conversation_id = chat_response.json()["conversation_id"]
    token_b = _register_and_login(client, "intruder@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    rename_response = client.patch(f"/conversations/{conversation_id}", json={"title": "اختراق"}, headers=headers_b)
    assert rename_response.status_code == 404
    delete_response = client.delete(f"/conversations/{conversation_id}", headers=headers_b)
    assert delete_response.status_code == 404


def test_create_conversation_summary(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تجريبي")),
    )
    monkeypatch.setattr(
        conversations_router_module,
        "get_ai_reply",
        AsyncMock(
            return_value=AIReply(
                text="- Topic: مناقشة مشروع\n- Key points: تم الاتفاق على الخطوات التالية",
                input_tokens=32,
                output_tokens=18,
            )
        ),
    )
    token = _register_and_login(client, "summary@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    conversation_id = client.post(
        "/chat",
        json={"message": "أريد تلخيص هذه المحادثة عن المشروع"},
        headers=headers,
    ).json()["conversation_id"]

    response = client.post(
        f"/conversations/{conversation_id}/summary",
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation_id"] == conversation_id
    assert "Topic" in payload["summary"]
    assert payload["summary_updated_at"]

    detail = client.get(f"/conversations/{conversation_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["summary"] == payload["summary"]
    assert detail.json()["summary_updated_at"] == payload["summary_updated_at"]


def test_cannot_summarize_other_users_conversation(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد تجريبي")),
    )
    token_a = _register_and_login(client, "summary-owner@example.com")
    conversation_id = client.post(
        "/chat",
        json={"message": "محادثة خاصة"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()["conversation_id"]

    token_b = _register_and_login(client, "summary-other@example.com")
    response = client.post(
        f"/conversations/{conversation_id}/summary",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_import_conversation_json_export_shape(client, monkeypatch):
    monkeypatch.setattr(
        chat_router_module,
        "get_ai_reply",
        AsyncMock(return_value=AIReply(text="رد")),
    )
    token = _register_and_login(client, "import@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    workspaces = client.get("/workspaces", headers=headers)
    assert workspaces.status_code == 200
    workspace_id = workspaces.json()[0]["id"]

    response = client.post(
        "/conversations/import",
        params={"workspace_id": workspace_id},
        json={
            "title": "محادثة مستوردة",
            "messages": [
                {"role": "user", "content": "سؤال مستورد", "sources": []},
                {"role": "assistant", "content": "جواب مستورد", "sources": []},
            ],
            "folder_id": None,
            "project_id": None,
        },
        headers=headers,
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "محادثة مستوردة"
    assert payload["workspace_id"] == workspace_id
    assert payload["is_pinned"] is False
    assert payload["is_archived"] is False
    assert payload["folder_id"] is None
    assert [message["content"] for message in payload["messages"]] == [
        "سؤال مستورد",
        "جواب مستورد",
    ]


def test_import_conversation_ignores_inaccessible_folder_and_project(client):
    token_a = _register_and_login(client, "import-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    workspace_a = client.get("/workspaces", headers=headers_a).json()[0]["id"]

    folder_a = client.post(
        "/folders",
        params={"workspace_id": workspace_a},
        json={"name": "Private"},
        headers=headers_a,
    ).json()

    token_b = _register_and_login(client, "import-other@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    workspace_b = client.get("/workspaces", headers=headers_b).json()[0]["id"]

    response = client.post(
        "/conversations/import",
        params={"workspace_id": workspace_b},
        json={
            "title": "Cross user import",
            "messages": [{"role": "user", "content": "test"}],
            "folder_id": folder_a["id"],
        },
        headers=headers_b,
    )
    assert response.status_code == 201
    assert response.json()["folder_id"] is None
    assert response.json()["workspace_id"] == workspace_b


def test_import_conversation_requires_workspace_membership(client):
    token_a = _register_and_login(client, "import-ws-owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    workspace_a = client.get("/workspaces", headers=headers_a).json()[0]["id"]

    token_b = _register_and_login(client, "import-ws-other@example.com")
    response = client.post(
        "/conversations/import",
        params={"workspace_id": workspace_a},
        json={
            "title": "Unauthorized",
            "messages": [{"role": "user", "content": "test"}],
        },
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404
