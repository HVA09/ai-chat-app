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
