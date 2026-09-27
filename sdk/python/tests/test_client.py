import httpx

from ai_chat_saas import AIChatClient, AuthenticationError, RateLimitError


def test_chat_maps_success_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat"
        assert request.headers["x-api-key"] == "ak_live_test"
        assert request.headers["accept"] == "application/json"
        assert request.json() == {"message": "hello", "model": "gpt-4o-mini"}
        return httpx.Response(
            200,
            json={"conversation_id": 7, "reply": "Hi!", "model": "gpt-4o-mini"},
            headers={"X-API-Version": "v1", "X-Request-ID": "req-123"},
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = AIChatClient(
            "ak_live_test",
            base_url="https://api.example.com/v1",
            http_client=http_client,
        )
        result = client.chat("hello", model="gpt-4o-mini")

    assert result.conversation_id == 7
    assert result.reply == "Hi!"
    assert result.model == "gpt-4o-mini"


def test_chat_maps_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"detail": "Invalid API key"},
            headers={"X-Request-ID": "req-auth"},
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = AIChatClient(
            "bad",
            base_url="https://api.example.com/v1",
            http_client=http_client,
        )

        try:
            client.chat("hello")
        except AuthenticationError as exc:
            assert exc.status_code == 401
            assert exc.request_id == "req-auth"
            assert str(exc) == "Invalid API key"
        else:
            raise AssertionError("AuthenticationError was not raised")


def test_chat_maps_rate_limit_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"detail": "Too many requests"},
            headers={"Retry-After": "30"},
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = AIChatClient(
            "ak_live_test",
            base_url="https://api.example.com/v1",
            http_client=http_client,
        )

        try:
            client.chat("hello")
        except RateLimitError as exc:
            assert exc.status_code == 429
            assert exc.retry_after == "30"
        else:
            raise AssertionError("RateLimitError was not raised")
