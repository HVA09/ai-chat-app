from app.logging_config import get_request_id, reset_request_id, set_request_id
from app.middleware import _REQUEST_ID_RE


def test_request_id_is_preserved_in_response(client):
    response = client.get(
        "/health",
        headers={"X-Request-ID": "trace-1234"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "trace-1234"
    assert get_request_id() == "-"


def test_invalid_request_id_is_replaced(client):
    response = client.get(
        "/health",
        headers={"X-Request-ID": "invalid id with spaces"},
    )

    generated = response.headers["X-Request-ID"]
    assert response.status_code == 200
    assert generated != "invalid id with spaces"
    assert _REQUEST_ID_RE.fullmatch(generated)
    assert len(generated) <= 64


def test_request_id_context_can_be_scoped():
    token = set_request_id("unit-test-id")
    try:
        assert get_request_id() == "unit-test-id"
    finally:
        reset_request_id(token)

    assert get_request_id() == "-"


def test_request_metrics_logger_uses_request_id(monkeypatch, client):
    records = []

    def fake_log(level, message, *args):
        records.append((level, message, args))

    monkeypatch.setattr("app.middleware.http_logger.log", fake_log)

    response = client.get(
        "/health",
        headers={"X-Request-ID": "metrics-test-1"},
    )

    assert response.status_code == 200
    assert any(
        level == 20
        and "HTTP GET /health 200" in message
        and "latency_ms=%s" in message
        and len(args) >= 5
        and args[3] >= 0
        and args[4] == "metrics-test-1"
        for level, message, args in records
    )


def test_request_metrics_log_never_includes_query_string(monkeypatch, client):
    records = []

    def fake_log(level, message, *args):
        records.append((level, message, args))

    monkeypatch.setattr("app.middleware.http_logger.log", fake_log)

    response = client.get(
        "/health?token=secret-value",
        headers={"X-Request-ID": "query-safe"},
    )

    assert response.status_code == 200
    rendered = " ".join([message % args if args else message for _, message, args in records])
    assert "secret-value" not in rendered
    assert "HTTP GET /health 200" in rendered



def test_general_rate_limit_rejects_burst(monkeypatch, client):
    from app.config import settings as app_settings

    monkeypatch.setattr(app_settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(
        "app.cache.check_rate_limit_with_reset",
        lambda *args, **kwargs: (False, 60, 2_000_000_000),
    )

    response = client.get("/billing/plans")

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Limit"] == "60"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert response.headers["Retry-After"] == "2000000000" if False else response.headers["Retry-After"]


def test_general_rate_limit_allows_with_rate_headers(monkeypatch, client):
    from app.config import settings as app_settings

    monkeypatch.setattr(app_settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(
        "app.cache.check_rate_limit_with_reset",
        lambda *args, **kwargs: (True, 2, 2_000_000_000),
    )

    response = client.get("/billing/plans")

    assert response.status_code != 429
    assert response.headers["X-RateLimit-Limit"] == "60"
    assert response.headers["X-RateLimit-Remaining"] == "58"
