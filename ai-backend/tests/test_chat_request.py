from pydantic import ValidationError

from app.schemas.chat import ChatRequest


def test_chat_request_allows_file_only_submission():
    payload = ChatRequest(file_ids=[123])

    assert payload.message == "أرسل لي الملف المرفق وحلله."
    assert payload.file_ids == [123]


def test_chat_request_rejects_empty_submission_without_files():
    try:
        ChatRequest()
    except ValidationError as exc:
        assert "يجب كتابة رسالة أو إرفاق ملف" in str(exc)
    else:
        raise AssertionError("ChatRequest should reject an empty submission")


def test_chat_request_strips_message():
    payload = ChatRequest(message="  hello  ")

    assert payload.message == "hello"
