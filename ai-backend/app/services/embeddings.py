"""خدمة embeddings لاستخدامها في فهرسة الملفات واسترجاع RAG."""
from __future__ import annotations

import math
from collections.abc import Sequence

import httpx

from app.config import settings

DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_EMBEDDING_DIMENSIONS = 768
MAX_EMBEDDING_BATCH = 32


class EmbeddingServiceError(RuntimeError):
    """خطأ قابل للعرض في اللوق عند فشل توليد embeddings."""


def _normalize(vector: Sequence[float]) -> list[float]:
    values = [float(value) for value in vector]
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]


def _gemini_url(action: str) -> str:
    base = settings.AI_API_BASE_URL.rstrip("/")
    if base.endswith("/openai"):
        base = base[: -len("/openai")].rstrip("/")
    return f"{base}/models/{settings.EMBEDDING_MODEL}:{action}"


def _extract_embedding_vectors(data: dict) -> list[list[float]]:
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


def _gemini_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.AI_API_KEY,
    }


def _openai_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.AI_API_KEY}",
    }


def embed_documents_sync(texts: Sequence[str]) -> list[list[float]]:
    """يولّد embeddings للمقاطع. الإخراج دائمًا بحجم EMBEDDING_DIMENSIONS."""
    if not texts:
        return []

    provider = settings.AI_PROVIDER.lower().strip()
    all_vectors: list[list[float]] = []

    with httpx.Client(timeout=45.0) as client:
        for start in range(0, len(texts), MAX_EMBEDDING_BATCH):
            batch = list(texts[start : start + MAX_EMBEDDING_BATCH])
            if provider == "gemini":
                payload = {
                    "requests": [
                        {
                            "model": f"models/{settings.EMBEDDING_MODEL}",
                            "content": {"parts": [{"text": text}]},
                            "taskType": "RETRIEVAL_DOCUMENT",
                            "outputDimensionality": settings.EMBEDDING_DIMENSIONS,
                        }
                        for text in batch
                    ]
                }
                response = client.post(
                    _gemini_url("batchEmbedContents"),
                    headers=_gemini_headers(),
                    json=payload,
                )
            else:
                payload = {
                    "model": settings.EMBEDDING_MODEL,
                    "input": batch,
                }
                if settings.EMBEDDING_DIMENSIONS:
                    payload["dimensions"] = settings.EMBEDDING_DIMENSIONS
                response = client.post(
                    f"{settings.AI_API_BASE_URL.rstrip('/')}/embeddings",
                    headers=_openai_headers(),
                    json=payload,
                )

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise EmbeddingServiceError(
                    f"فشل توليد embeddings: HTTP {response.status_code}"
                ) from exc

            vectors = _extract_embedding_vectors(response.json())
            if len(vectors) != len(batch):
                raise EmbeddingServiceError("عدد embeddings لا يطابق عدد المقاطع")
            all_vectors.extend(vectors)

    return all_vectors


async def embed_query(text: str) -> list[float]:
    """يولّد embedding لسؤال المستخدم باستخدام مهمة الاسترجاع."""
    provider = settings.AI_PROVIDER.lower().strip()

    async with httpx.AsyncClient(timeout=30.0) as client:
        if provider == "gemini":
            payload = {
                "model": f"models/{settings.EMBEDDING_MODEL}",
                "content": {"parts": [{"text": text}]},
                "taskType": "RETRIEVAL_QUERY",
                "outputDimensionality": settings.EMBEDDING_DIMENSIONS,
            }
            response = await client.post(
                _gemini_url("embedContent"),
                headers=_gemini_headers(),
                json=payload,
            )
        else:
            payload = {
                "model": settings.EMBEDDING_MODEL,
                "input": text,
            }
            if settings.EMBEDDING_DIMENSIONS:
                payload["dimensions"] = settings.EMBEDDING_DIMENSIONS
            response = await client.post(
                f"{settings.AI_API_BASE_URL.rstrip('/')}/embeddings",
                headers=_openai_headers(),
                json=payload,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise EmbeddingServiceError(
                f"فشل توليد embedding للسؤال: HTTP {response.status_code}"
            ) from exc

        vectors = _extract_embedding_vectors(response.json())
        if len(vectors) != 1:
            raise EmbeddingServiceError("المزوّد لم يُرجع embedding واحدًا للسؤال")
        return vectors[0]
