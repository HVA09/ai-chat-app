"""Regression tests for independent embedding-provider configuration."""
import asyncio

import pytest

from app.services import embeddings


def _set_embedding_settings(monkeypatch, **overrides):
    values = {
        "AI_PROVIDER": "openai",
        "AI_API_KEY": "chat-secret",
        "AI_API_BASE_URL": "https://api.openai.com/v1",
        "EMBEDDING_PROVIDER": "",
        "EMBEDDING_API_KEY": "",
        "EMBEDDING_API_BASE_URL": "",
        "EMBEDDING_MODEL": "",
        "EMBEDDING_DIMENSIONS": 3,
    }
    values.update(overrides)
    for name, value in values.items():
        monkeypatch.setattr(embeddings.settings, name, value)
    # Test API payload sizes without changing the real PostgreSQL vector schema.
    monkeypatch.setattr(
        embeddings, "STORED_EMBEDDING_DIMENSIONS", values["EMBEDDING_DIMENSIONS"]
    )


def test_existing_render_gemini_compat_config_resolves_native_embedding_endpoint(monkeypatch):
    """Cover the user's current non-secret Render configuration shape."""
    _set_embedding_settings(
        monkeypatch,
        AI_PROVIDER="gemini",
        AI_API_KEY="chat-secret",
        AI_API_BASE_URL=(
            "https://generativelanguage.googleapis.com/v1beta/openai/"
        ),
        EMBEDDING_PROVIDER="",
        EMBEDDING_API_KEY="",
        EMBEDDING_API_BASE_URL="",
        EMBEDDING_MODEL="",
        EMBEDDING_DIMENSIONS=768,
    )

    config = embeddings._resolve_embedding_config()

    assert config.provider == "gemini"
    assert config.model == "gemini-embedding-001"
    assert config.api_key == "chat-secret"
    assert config.base_url == "https://generativelanguage.googleapis.com/v1beta"


def test_defaults_choose_an_embedding_model_compatible_with_chat_provider(monkeypatch):
    _set_embedding_settings(monkeypatch)

    config = embeddings._resolve_embedding_config()

    assert config.provider == "openai"
    assert config.model == "text-embedding-3-small"
    assert config.api_key == "chat-secret"
    assert config.base_url == "https://api.openai.com/v1"


def test_embedding_provider_can_use_separate_gemini_credentials_and_base_url(monkeypatch):
    _set_embedding_settings(
        monkeypatch,
        AI_PROVIDER="openai",
        AI_API_KEY="chat-secret",
        AI_API_BASE_URL="https://api.openai.com/v1",
        EMBEDDING_PROVIDER="gemini",
        EMBEDDING_API_KEY="embedding-secret",
        EMBEDDING_API_BASE_URL=(
            "https://generativelanguage.googleapis.com/v1beta/openai"
        ),
        EMBEDDING_MODEL="gemini-embedding-001",
    )

    config = embeddings._resolve_embedding_config()

    assert config.provider == "gemini"
    assert config.api_key == "embedding-secret"
    assert config.base_url == "https://generativelanguage.googleapis.com/v1beta"
    assert config.model == "gemini-embedding-001"


def test_mismatched_legacy_model_fails_closed_without_rerouting_chat_key(
    monkeypatch,
):
    _set_embedding_settings(
        monkeypatch,
        AI_PROVIDER="openai",
        AI_API_KEY="openai-chat-secret",
        AI_API_BASE_URL="https://api.openai.com/v1",
        EMBEDDING_MODEL="gemini-embedding-001",
    )

    with pytest.raises(embeddings.EmbeddingServiceError, match="EMBEDDING_PROVIDER=gemini"):
        embeddings._resolve_embedding_config()


def test_unsupported_explicit_embedding_provider_is_rejected(monkeypatch):
    _set_embedding_settings(monkeypatch, EMBEDDING_PROVIDER="anthropic")

    with pytest.raises(embeddings.EmbeddingServiceError, match="EMBEDDING_PROVIDER"):
        embeddings._resolve_embedding_config()


def test_gemini_singular_response_is_parsed_and_dimension_checked(monkeypatch):
    _set_embedding_settings(monkeypatch, EMBEDDING_PROVIDER="gemini")

    vectors = embeddings._extract_embedding_vectors(
        {"embedding": {"values": [3.0, 4.0, 0.0]}}
    )
    validated = embeddings._validate_embedding_vectors(vectors, 1)

    assert len(validated) == 1
    assert len(validated[0]) == 3
    assert validated[0][0] == pytest.approx(0.6)
    assert validated[0][1] == pytest.approx(0.8)


def test_embedding_dimension_mismatch_is_reported(monkeypatch):
    _set_embedding_settings(monkeypatch, EMBEDDING_DIMENSIONS=768)

    with pytest.raises(embeddings.EmbeddingServiceError, match="أبعاد embedding"):
        embeddings._validate_embedding_vectors([[0.1, 0.2, 0.3]], 1)


def test_query_uses_independent_gemini_api_and_parses_native_response(
    monkeypatch,
):
    _set_embedding_settings(
        monkeypatch,
        AI_PROVIDER="openai",
        AI_API_KEY="chat-secret",
        AI_API_BASE_URL="https://api.openai.com/v1",
        EMBEDDING_PROVIDER="gemini",
        EMBEDDING_API_KEY="embedding-secret",
        EMBEDDING_MODEL="gemini-embedding-001",
        EMBEDDING_DIMENSIONS=3,
    )
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"embedding": {"values": [3.0, 4.0, 0.0]}}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, *, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(embeddings.httpx, "AsyncClient", FakeAsyncClient)

    vector = asyncio.run(embeddings.embed_query("A Linux networking question"))

    assert len(vector) == 3
    assert captured["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-embedding-001:embedContent"
    )
    assert captured["headers"]["x-goog-api-key"] == "embedding-secret"
    assert "Authorization" not in captured["headers"]
    assert captured["json"]["embedContentConfig"] == {
        "taskType": "RETRIEVAL_QUERY",
        "outputDimensionality": 3,
    }


def test_document_embeddings_use_openai_compatible_endpoint_and_separate_key(
    monkeypatch,
):
    _set_embedding_settings(
        monkeypatch,
        AI_PROVIDER="gemini",
        AI_API_KEY="chat-secret",
        AI_API_BASE_URL="https://chat.example/v1",
        EMBEDDING_PROVIDER="openai",
        EMBEDDING_API_KEY="embedding-secret",
        EMBEDDING_API_BASE_URL="https://embeddings.example/v1",
        EMBEDDING_MODEL="text-embedding-3-small",
        EMBEDDING_DIMENSIONS=3,
    )
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {"embedding": [1.0, 0.0, 0.0], "index": 0},
                    {"embedding": [0.0, 1.0, 0.0], "index": 1},
                ]
            }

    class FakeSyncClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def post(self, url, *, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(embeddings.httpx, "Client", FakeSyncClient)

    vectors = embeddings.embed_documents_sync(["Linux", "TCP/IP"])

    assert len(vectors) == 2
    assert all(len(vector) == 3 for vector in vectors)
    assert captured["url"] == "https://embeddings.example/v1/embeddings"
    assert captured["headers"]["Authorization"] == "Bearer embedding-secret"
    assert captured["json"]["model"] == "text-embedding-3-small"
    assert captured["json"]["dimensions"] == 3
    assert captured["json"]["input"] == ["Linux", "TCP/IP"]


def test_document_embeddings_use_native_gemini_batch_endpoint(monkeypatch):
    _set_embedding_settings(
        monkeypatch,
        AI_PROVIDER="openai",
        AI_API_KEY="chat-secret",
        EMBEDDING_PROVIDER="gemini",
        EMBEDDING_API_KEY="embedding-secret",
        EMBEDDING_MODEL="gemini-embedding-001",
        EMBEDDING_DIMENSIONS=3,
    )
    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "embeddings": [
                    {"values": [1.0, 0.0, 0.0]},
                    {"values": [0.0, 1.0, 0.0]},
                ]
            }

    class FakeSyncClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def post(self, url, *, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(embeddings.httpx, "Client", FakeSyncClient)

    vectors = embeddings.embed_documents_sync(["Linux", "TCP/IP"])

    assert len(vectors) == 2
    assert captured["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-embedding-001:batchEmbedContents"
    )
    assert captured["headers"]["x-goog-api-key"] == "embedding-secret"
    assert "Authorization" not in captured["headers"]
    first_request = captured["json"]["requests"][0]
    assert first_request["model"] == "models/gemini-embedding-001"
    assert first_request["embedContentConfig"] == {
        "taskType": "RETRIEVAL_DOCUMENT",
        "outputDimensionality": 3,
    }


@pytest.mark.parametrize("chat_provider", ["anthropic", "deepseek"])
def test_unsupported_chat_provider_requires_explicit_embedding_provider(
    monkeypatch, chat_provider
):
    _set_embedding_settings(monkeypatch, AI_PROVIDER=chat_provider)

    with pytest.raises(embeddings.EmbeddingServiceError, match="لا يوجد تكامل embeddings"):
        embeddings._resolve_embedding_config()


def test_separate_provider_requires_its_own_api_key(monkeypatch):
    _set_embedding_settings(
        monkeypatch,
        AI_PROVIDER="openai",
        AI_API_KEY="openai-chat-secret",
        EMBEDDING_PROVIDER="gemini",
        EMBEDDING_API_KEY="",
        EMBEDDING_MODEL="gemini-embedding-001",
    )

    with pytest.raises(embeddings.EmbeddingServiceError, match="EMBEDDING_API_KEY"):
        embeddings._resolve_embedding_config()


def test_separate_openai_embeddings_use_openai_root_not_chat_provider_base(
    monkeypatch,
):
    _set_embedding_settings(
        monkeypatch,
        AI_PROVIDER="gemini",
        AI_API_KEY="chat-secret",
        AI_API_BASE_URL=(
            "https://generativelanguage.googleapis.com/v1beta/openai"
        ),
        EMBEDDING_PROVIDER="openai",
        EMBEDDING_API_KEY="embedding-secret",
        EMBEDDING_API_BASE_URL="",
        EMBEDDING_MODEL="text-embedding-3-small",
    )

    config = embeddings._resolve_embedding_config()

    assert config.provider == "openai"
    assert config.base_url == "https://api.openai.com/v1"
    assert config.api_key == "embedding-secret"


def test_openai_compatible_provider_requires_its_own_api_base_when_independent(
    monkeypatch,
):
    _set_embedding_settings(
        monkeypatch,
        AI_PROVIDER="gemini",
        EMBEDDING_PROVIDER="openai-compatible",
        EMBEDDING_API_KEY="embedding-secret",
        EMBEDDING_API_BASE_URL="",
    )

    with pytest.raises(embeddings.EmbeddingServiceError, match="EMBEDDING_API_BASE_URL"):
        embeddings._resolve_embedding_config()


def test_embedding_dimensions_must_match_existing_database_vector_schema(
    monkeypatch,
):
    _set_embedding_settings(monkeypatch, EMBEDDING_DIMENSIONS=768)
    monkeypatch.setattr(embeddings, "STORED_EMBEDDING_DIMENSIONS", 1536)

    with pytest.raises(
        embeddings.EmbeddingServiceError,
        match="يجب أن يطابق بُعد المتجهات",
    ):
        embeddings._resolve_embedding_config()

@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_embedding_normalization_rejects_non_finite_values(monkeypatch, bad_value):
    _set_embedding_settings(monkeypatch, EMBEDDING_DIMENSIONS=3)

    with pytest.raises(
        embeddings.EmbeddingServiceError,
        match="غير منتهية",
    ):
        embeddings._extract_embedding_vectors(
            {"embedding": {"values": [bad_value, 0.0, 0.0]}}
        )


def test_embedding_validation_rejects_non_finite_values(monkeypatch):
    _set_embedding_settings(monkeypatch, EMBEDDING_DIMENSIONS=3)

    with pytest.raises(
        embeddings.EmbeddingServiceError,
        match="غير منتهية",
    ):
        embeddings._validate_embedding_vectors([[float("nan"), 0.0, 0.0]], 1)


def test_embedding_rejects_zero_vector(monkeypatch):
    _set_embedding_settings(monkeypatch, EMBEDDING_DIMENSIONS=3)

    with pytest.raises(
        embeddings.EmbeddingServiceError,
        match="صفري",
    ):
        embeddings._extract_embedding_vectors(
            {"embedding": {"values": [0.0, 0.0, 0.0]}}
        )


def test_embedding_rejects_non_numeric_values(monkeypatch):
    _set_embedding_settings(monkeypatch, EMBEDDING_DIMENSIONS=3)

    with pytest.raises(
        embeddings.EmbeddingServiceError,
        match="غير رقمية",
    ):
        embeddings._extract_embedding_vectors(
            {"embedding": {"values": [1.0, "not-a-number", 0.0]}}
        )
