"""Offline RAG retrieval ranking and metric helpers.

This module does not call a model or a provider. Callers provide vectors generated
by the configured embedding service and can evaluate those vectors deterministically.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Compute cosine similarity with strict checks for malformed vectors."""
    if not left or not right or len(left) != len(right):
        raise ValueError("Embedding vectors must be non-empty and have equal dimensions.")

    left_values = [float(value) for value in left]
    right_values = [float(value) for value in right]
    if any(not math.isfinite(value) for value in (*left_values, *right_values)):
        raise ValueError("Embedding vectors must contain only finite numbers.")

    left_norm = math.sqrt(sum(value * value for value in left_values))
    right_norm = math.sqrt(sum(value * value for value in right_values))
    if not math.isfinite(left_norm) or not math.isfinite(right_norm):
        raise ValueError("Embedding vector norm is outside the supported numeric range.")
    if left_norm == 0 or right_norm == 0:
        raise ValueError("Cosine similarity is undefined for a zero vector.")

    similarity = sum(a * b for a, b in zip(left_values, right_values, strict=True)) / (
        left_norm * right_norm
    )
    if not math.isfinite(similarity):
        raise ValueError("Cosine similarity calculation returned a non-finite value.")
    return similarity


def rank_documents(
    query_embedding: Sequence[float],
    documents: Sequence[Mapping[str, Any]],
    document_embeddings: Sequence[Sequence[float]],
) -> list[tuple[str, float]]:
    """Return (document id, cosine similarity) pairs, highest score first."""
    if len(documents) != len(document_embeddings):
        raise ValueError("Each document must have exactly one embedding.")

    scored: list[tuple[str, float, int]] = []
    seen_ids: set[str] = set()
    for position, (document, embedding) in enumerate(
        zip(documents, document_embeddings, strict=True)
    ):
        document_id = document.get("id")
        if not isinstance(document_id, str) or not document_id:
            raise ValueError("Each document must have a non-empty string id.")
        if document_id in seen_ids:
            raise ValueError(f"Duplicate document id: {document_id}")
        seen_ids.add(document_id)
        scored.append(
            (document_id, cosine_similarity(query_embedding, embedding), position)
        )

    scored.sort(key=lambda item: (-item[1], item[2]))
    return [(document_id, score) for document_id, score, _position in scored]


def score_ranked_results(
    ranked_document_ids: Sequence[str],
    relevance_by_id: Mapping[str, int],
    k: int = 3,
) -> dict[str, float]:
    """Calculate Recall@k, Precision@k and reciprocal rank for one query."""
    if k < 1:
        raise ValueError("k must be at least 1.")
    if len(ranked_document_ids) != len(set(ranked_document_ids)):
        raise ValueError("Ranked document ids must be unique.")
    missing = set(ranked_document_ids) - set(relevance_by_id)
    if missing:
        raise ValueError(f"Missing relevance labels for documents: {sorted(missing)}")

    if any(
        isinstance(relevance, bool)
        or not isinstance(relevance, int)
        or relevance not in {0, 1, 2}
        for relevance in relevance_by_id.values()
    ):
        raise ValueError("Relevance labels must be integer grades 0, 1, or 2.")

    relevant_ids = {
        document_id
        for document_id, relevance in relevance_by_id.items()
        if relevance > 0
    }
    top_ids = list(ranked_document_ids[:k])
    hits = sum(1 for document_id in top_ids if relevance_by_id[document_id] > 0)
    recall = hits / len(relevant_ids) if relevant_ids else 0.0
    precision = hits / k

    reciprocal_rank = 0.0
    for rank, document_id in enumerate(ranked_document_ids, start=1):
        if relevance_by_id[document_id] > 0:
            reciprocal_rank = 1.0 / rank
            break

    def discounted_gain(relevance_grades: Sequence[int]) -> float:
        return sum(
            (2**relevance - 1) / math.log2(rank + 1)
            for rank, relevance in enumerate(relevance_grades[:k], start=1)
        )

    actual_grades = [relevance_by_id[document_id] for document_id in ranked_document_ids]
    ideal_grades = sorted(relevance_by_id.values(), reverse=True)
    ideal_dcg = discounted_gain(ideal_grades)
    ndcg = discounted_gain(actual_grades) / ideal_dcg if ideal_dcg else 0.0

    return {
        f"recall_at_{k}": recall,
        f"precision_at_{k}": precision,
        f"ndcg_at_{k}": ndcg,
        "reciprocal_rank": reciprocal_rank,
    }
