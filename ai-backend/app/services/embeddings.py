"""خدمة embeddings مستقلة عن مزوّد المحادثة، لفهرسة الملفات واسترجاع RAG."""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from app.config import settings


GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_EMBEDDING_MODELS = {
    "gemini": "gemini-embedding-001",
    "openai": "text-embedding-3-small",
    "openai-compatible": "text-embedding-3-small",
}
SUPPORTED_EMBEDDING_PROVIDERS = frozenset(DEFAULT_EMBEDDING_MODELS)
MAX_EMBEDDING_BATCH = 32


class EmbeddingServiceError(RuntimeError):
    """خطأ آمن نسبيًا يمكن تسجيله عند فشل خدمة embeddings."""


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    api_key: str
    base_url: str
    model: str


def _normalize(vector: Sequence[float]) -> list[float]:
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]


def _normalize_gemini_base_url(base_url: str) -> str:
    """Convert a Gemini API root or OpenAI-compat URL to its native REST root."""
    base = base_url.strip().rstrip("/")
    if not base:
        return GEMINI_BASE_URL
    if base.endswith("/openai"):
        base = base[: -len("/openai")].rstrip("/")
    if base.endswith("/v1beta"):
        return base
    return f"{base}/v1beta"


def _resolve_embedding_config() -> EmbeddingConfig:
    """Resolve independent embedding settings while preserving older deployments.

    EMBEDDING_PROVIDER can override the chat provider. If omitted, provider
    selection follows AI_PROVIDER, except when an explicitly configured model
    clearly identifies the Gemini or OpenAI embedding family.
    """
    configured_provider = (settings.EMBEDDING_PROVIDER or "").strip().lower()
    configured_model = (settings.EMBEDDING_MODEL or "").strip()
    chat_provider = (settings.AI_PROVIDER or "").strip().lower()

    provider = configured_provider or chat_provider

    if configured_provider and provider not in SUPPORTED_EMBEDDING_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_EMBEDDING_PROVIDERS))
        raise EmbeddingServiceError(
            f"EMBEDDING_PROVIDER غير مدعوم. الخيارات المتاحة: {supported}"
        )

    # Historically, all non-Gemini providers used the OpenAI-compatible
    # /embeddings endpoint. Keep that route for older provider names, but do
    # not route a provider-specific model to another vendor by guessing.
    if provider not in SUPPORTED_EMBEDDING_PROVIDERS:
        provider = "openai-compatible"

    model = configured_model or DEFAULT_EMBEDDING_MODELS[provider]
    if model.startswith("gemini-embedding-") and provider != "gemini":
        raise EmbeddingServiceError(
            "EMBEDDING_MODEL من عائلة Gemini لكن مزوّد embeddings ليس Gemini. "
            "اضبط EMBEDDING_PROVIDER=gemini ومفتاح Gemini المناسب."
        )
    if model.startswith("text-embedding-") and provider not in {
        "openai",
        "openai-compatible",
    }:
        raise EmbeddingServiceError(
            "EMBEDDING_MODEL من عائلة OpenAI لكن مزوّد embeddings غير متوافق. "
            "اضبط EMBEDDING_PROVIDER الصحيح."
        )
    api_key = (
        (settings.EMBEDDING_API_KEY or "").strip()
        or (settings.AI_API_KEY or "").strip()
    )
    configured_base_url = (settings.EMBEDDING_API_BASE_URL or "").strip()
    chat_base_url = (settings.AI_API_BASE_URL or "").strip()

    if not api_key:
        raise EmbeddingServiceError(
            "مفتاح embeddings غير مضبوط. عيّن EMBEDDING_API_KEY أو AI_API_KEY."
        )
    if settings.EMBEDDING_DIMENSIONS <= 0:
        raise EmbeddingServiceError("EMBEDDING_DIMENSIONS يجب أن يكون عددًا موجبًا.")

    if provider == "gemini":
        if configured_base_url:
            base_url = _normalize_gemini_base_url(configured_base_url)
        elif (
            not configured_provider
            and "generativelanguage.googleapis.com" in chat_base_url
        ):
            # Preserve existing Gemini-compatible deployments that put
            # /v1beta/openai in AI_API_BASE_URL.
            base_url = _normalize_gemini_base_url(chat_base_url)
        else:
            base_url = GEMINI_BASE_URL
    else:
        base_url = (configured_base_url or chat_base_url).rstrip("/")
        if not base_url:
            raise EmbeddingServiceError(
                "عنوان خدمة embeddings غير مضبوط. عيّن EMBEDDING_API_BASE_URL أو AI_API_BASE_URL."
            )

    return EmbeddingConfig(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


def _embedding_headers(config: EmbeddingConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.provider == "gemini":
        headers["x-goog-api-key"] = config.api_key
    else:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


def _embedding_url(config: EmbeddingConfig, gemini_action: str) -> str:
    if config.provider == "gemini":
        return f"{config.base_url}/models/{config.model}:{gemini_action}"
    return f"{config.base_url}/embeddings"


def _extract_embedding_vectors(data: dict) -> list[list[float]]:
    """Read both Gemini's singular embedContent response and batch/OpenAI responses."""
    single_embedding = data.get("embedding")
    if isinstance(single_embedding, dict) and isinstance(
        single_embedding.get("values"), list
    ):
        return [_normalize(single_embedding["values"])]

    embeddings = data.get("embeddings")
    if isinstance(embeddings, list):
        vectors = []
        for item in embeddings:
            if isinstance(item, dict) and isinstance(item.get("values"), list):
                vectors.append(_normalize(item["values"]))
        if vectors:
            return vectors

    data_items = data.get("data")
    if isinstance(data_items, list):
        vectors = []
        for item in data_items:
            if isinstance(item, dict) and isinstance(item.get("embedding"), list):
                vectors.append(_normalize(item["embedding"]))
        if vectors:
            return vectors

    raise EmbeddingServiceError("صيغة embeddings غير متوقعة من مزوّد الذكاء الاصطناعي")


def _validate_embedding_vectors(
    vectors: list[list[float]], expected_count: int
) -> list[list[float]]:
    if len(vectors) != expected_count:
        raise EmbeddingServiceError("عدد embeddings لا يطابق عدد المدخلات")

    expected_dimensions = settings.EMBEDDING_DIMENSIONS
    for vector in vectors:
        if len(vector) != expected_dimensions:
            raise EmbeddingServiceError(
                "أبعاد embedding لا تطابق مخطط قاعدة البيانات: "
                f"المتوقع {expected_dimensions}، والمستلم {len(vector)}."
            )
    return vectors


def _gemini_embedding_config(task_type: str) -> dict[str, str | int]:
    return {
        "taskType": task_type,
        "outputDimensionality": settings.EMBEDDING_DIMENSIONS,
    }


def embed_documents_sync(texts: Sequence[str]) -> list[list[float]]:
    """Generate document embeddings with the configured embedding provider."""
    if not texts:
        return []

    config = _resolve_embedding_config()
    all_vectors: list[list[float]] = []

    try:
        with httpx.Client(timeout=45.0) as client:
            for start in range(0, len(texts), MAX_EMBEDDING_BATCH):
                batch = list(texts[start : start + MAX_EMBEDDING_BATCH])
                if config.provider == "gemini":
                    payload = {
                        "requests": [
                            {
                                "model": f"models/{config.model}",
                                "content": {"parts": [{"text": text}]},
                                "embedContentConfig": _gemini_embedding_config(
                                    "RETRIEVAL_DOCUMENT"
                                ),
                            }
                            for text in batch
                        ]
                    }
                    response = client.post(
                        _embedding_url(config, "batchEmbedContents"),
                        headers=_embedding_headers(config),
                        json=payload,
                    )
                else:
                    payload = {
                        "model": config.model,
                        "input": batch,
                        "dimensions": settings.EMBEDDING_DIMENSIONS,
                    }
                    response = client.post(
                        _embedding_url(config, "embedContent"),
                        headers=_embedding_headers(config),
                        json=payload,
                    )

                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise EmbeddingServiceError(
                        f"فشل توليد embeddings: HTTP {response.status_code}"
                    ) from exc

                vectors = _extract_embedding_vectors(response.json())
                all_vectors.extend(_validate_embedding_vectors(vectors, len(batch)))
    except httpx.RequestError as exc:
        raise EmbeddingServiceError("تعذر الاتصال بمزوّد embeddings") from exc

    return all_vectors


async def embed_query(text: str) -> list[float]:
    """Generate an embedding for a query using the same provider/model as indexing."""
    config = _resolve_embedding_config()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if config.provider == "gemini":
                payload = {
                    "model": f"models/{config.model}",
                    "content": {"parts": [{"text": text}]},
                    "embedContentConfig": _gemini_embedding_config("RETRIEVAL_QUERY"),
                }
            else:
                payload = {
                    "model": config.model,
                    "input": text,
                    "dimensions": settings.EMBEDDING_DIMENSIONS,
                }

            response = await client.post(
                _embedding_url(config, "embedContent"),
                headers=_embedding_headers(config),
                json=payload,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise EmbeddingServiceError(
                    f"فشل توليد embedding للسؤال: HTTP {response.status_code}"
                ) from exc

            vectors = _extract_embedding_vectors(response.json())
            validated = _validate_embedding_vectors(vectors, 1)
            return validated[0]
    except httpx.RequestError as exc:
        # The chat route can use its existing full-text fallback if embeddings
        # cannot be reached; do not expose upstream credentials or response data.
        raise EmbeddingServiceError("تعذر الاتصال بمزوّد embeddings") from exc
