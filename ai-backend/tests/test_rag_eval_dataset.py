"""Offline integrity and metric tests for the RAG retrieval evaluation benchmark."""
import json
from collections import Counter
from pathlib import Path

import pytest

from app.services.rag_evaluation import (
    cosine_similarity,
    rank_documents,
    score_ranked_results,
)

EVALUATION_FILE = (
    Path(__file__).parent / "fixtures" / "rag_retrieval_eval_cases.json"
)
EXPECTED_DOMAINS = {
    "networking",
    "linux",
    "programming",
    "cloud",
    "security",
    "database",
    "teaching",
}
REQUIRED_CASE_FIELDS = {
    "id",
    "domain",
    "query",
    "documents",
    "critical_failure",
}
REQUIRED_DOCUMENT_FIELDS = {"id", "relevance", "title", "text"}


def _load_dataset():
    with EVALUATION_FILE.open(encoding="utf-8") as source:
        dataset = json.load(source)
    assert dataset["schema_version"] == 1
    assert isinstance(dataset.get("cases"), list)
    return dataset["cases"]


def test_rag_evaluation_cases_have_complete_unique_ids_and_relevance_labels():
    cases = _load_dataset()
    assert len(cases) >= 10

    case_ids = [case.get("id") for case in cases]
    assert all(isinstance(case_id, str) and case_id for case_id in case_ids)
    assert len(case_ids) == len(set(case_ids))

    all_document_ids = []
    for case in cases:
        assert REQUIRED_CASE_FIELDS <= case.keys(), case.get("id")
        assert case["domain"] in EXPECTED_DOMAINS, case["id"]
        assert isinstance(case["query"], str) and len(case["query"].strip()) >= 20
        assert isinstance(case["critical_failure"], str) and case["critical_failure"].strip()
        documents = case["documents"]
        assert len(documents) >= 3, case["id"]

        for document in documents:
            assert REQUIRED_DOCUMENT_FIELDS <= document.keys(), case["id"]
            assert isinstance(document["id"], str) and document["id"]
            assert document["relevance"] in {0, 1, 2}
            assert isinstance(document["title"], str) and document["title"].strip()
            assert isinstance(document["text"], str) and len(document["text"].strip()) >= 30
            all_document_ids.append(document["id"])

        relevance_levels = [document["relevance"] for document in documents]
        assert 2 in relevance_levels, f"{case['id']} needs a highly relevant document"
        assert 0 in relevance_levels, f"{case['id']} needs at least one hard negative"

    assert len(all_document_ids) == len(set(all_document_ids))
    assert EXPECTED_DOMAINS <= {case["domain"] for case in cases}


def test_rag_evaluation_dataset_has_cases_across_all_domains():
    counts = Counter(case["domain"] for case in _load_dataset())
    for domain in EXPECTED_DOMAINS:
        assert counts[domain] >= 1, f"Missing RAG evaluation coverage for {domain}"


def test_cosine_similarity_handles_known_vectors():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


@pytest.mark.parametrize(
    "left,right",
    [
        ([], []),
        ([1.0, 0.0], [1.0]),
        ([0.0, 0.0], [1.0, 0.0]),
        ([float("nan"), 0.0], [1.0, 0.0]),
        ([float("inf"), 0.0], [1.0, 0.0]),
    ],
)
def test_cosine_similarity_rejects_invalid_vectors(left, right):
    with pytest.raises(ValueError):
        cosine_similarity(left, right)


def test_rank_documents_orders_closest_document_first_and_is_stable():
    documents = [
        {"id": "relevant", "relevance": 2},
        {"id": "negative", "relevance": 0},
        {"id": "partially-relevant", "relevance": 1},
    ]
    vectors = [
        [1.0, 0.0],
        [0.0, 1.0],
        [0.8, 0.6],
    ]

    ranked = rank_documents([1.0, 0.0], documents, vectors)

    assert [document_id for document_id, _score in ranked] == [
        "relevant",
        "partially-relevant",
        "negative",
    ]
    assert ranked[0][1] == pytest.approx(1.0)


def test_rank_documents_rejects_count_mismatch_and_duplicate_ids():
    with pytest.raises(ValueError, match="exactly one embedding"):
        rank_documents([1.0], [{"id": "doc"}], [])

    with pytest.raises(ValueError, match="Duplicate document id"):
        rank_documents(
            [1.0, 0.0],
            [{"id": "same"}, {"id": "same"}],
            [[1.0, 0.0], [0.0, 1.0]],
        )


def test_retrieval_metrics_calculate_recall_precision_and_reciprocal_rank():
    scores = score_ranked_results(
        ["negative", "partial", "relevant"],
        {"negative": 0, "partial": 1, "relevant": 2},
        k=3,
    )

    assert scores["recall_at_3"] == pytest.approx(1.0)
    assert scores["precision_at_3"] == pytest.approx(2 / 3)
    assert scores["reciprocal_rank"] == pytest.approx(0.5)


def test_retrieval_metrics_allow_no_relevant_documents_without_division_error():
    scores = score_ranked_results(
        ["first", "second"],
        {"first": 0, "second": 0},
        k=3,
    )

    assert scores["recall_at_3"] == 0.0
    assert scores["precision_at_3"] == 0.0
    assert scores["reciprocal_rank"] == 0.0


def test_retrieval_metrics_reject_bad_k_duplicates_and_missing_labels():
    with pytest.raises(ValueError, match="at least 1"):
        score_ranked_results(["doc"], {"doc": 1}, k=0)

    with pytest.raises(ValueError, match="unique"):
        score_ranked_results(["doc", "doc"], {"doc": 1})

    with pytest.raises(ValueError, match="Missing relevance labels"):
        score_ranked_results(["unknown"], {}, k=1)
