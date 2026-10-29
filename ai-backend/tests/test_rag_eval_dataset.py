"""Offline integrity and metric tests for the RAG retrieval evaluation benchmark."""
import importlib.util
import json
import re
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


def test_rag_fixture_declares_all_metrics_produced_by_benchmark():
    with EVALUATION_FILE.open(encoding="utf-8") as source:
        dataset = json.load(source)

    assert set(dataset["metrics"]) == {
        "recall_at_3",
        "precision_at_3",
        "ndcg_at_3",
        "reciprocal_rank",
    }


def test_rag_evaluation_cases_have_complete_unique_ids_and_relevance_labels():
    cases = _load_dataset()
    assert len(cases) >= 20

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
        assert len(documents) >= 5, case["id"]

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
        assert sum(grade == 0 for grade in relevance_levels) >= 3, (
            f"{case['id']} needs enough negative candidates for meaningful top-k metrics"
        )

    assert len(all_document_ids) == len(set(all_document_ids))
    assert EXPECTED_DOMAINS <= {case["domain"] for case in cases}


def test_rag_evaluation_dataset_has_cases_across_all_domains():
    cases = _load_dataset()
    counts = Counter(case["domain"] for case in cases)
    for domain in EXPECTED_DOMAINS:
        assert counts[domain] >= 2, f"Expected at least two RAG evaluation cases for {domain}"


def test_rag_evaluation_dataset_covers_arabic_queries_in_every_domain():
    cases = _load_dataset()
    arabic_query_domains = {
        case["domain"]
        for case in cases
        if re.search(r"[\u0600-\u06FF]", case["query"])
    }

    assert EXPECTED_DOMAINS <= arabic_query_domains


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
    assert 0.0 < scores["ndcg_at_3"] < 1.0
    assert scores["reciprocal_rank"] == pytest.approx(0.5)


def test_retrieval_ndcg_is_one_for_perfect_graded_ranking():
    scores = score_ranked_results(
        ["high", "partial", "negative"],
        {"high": 2, "partial": 1, "negative": 0},
        k=3,
    )

    assert scores["ndcg_at_3"] == pytest.approx(1.0)


def test_retrieval_metrics_allow_no_relevant_documents_without_division_error():
    scores = score_ranked_results(
        ["first", "second"],
        {"first": 0, "second": 0},
        k=3,
    )

    assert scores["recall_at_3"] == 0.0
    assert scores["precision_at_3"] == 0.0
    assert scores["ndcg_at_3"] == 0.0
    assert scores["reciprocal_rank"] == 0.0


def test_retrieval_metrics_reject_bad_k_duplicates_and_missing_labels():
    with pytest.raises(ValueError, match="at least 1"):
        score_ranked_results(["doc"], {"doc": 1}, k=0)

    with pytest.raises(ValueError, match="unique"):
        score_ranked_results(["doc", "doc"], {"doc": 1})

    with pytest.raises(ValueError, match="Missing relevance labels"):
        score_ranked_results(["unknown"], {}, k=1)

    with pytest.raises(ValueError, match="integer grades 0, 1, or 2"):
        score_ranked_results(["doc"], {"doc": 3}, k=1)


def test_benchmark_runner_calculates_metrics_without_live_provider_calls(monkeypatch):
    runner_path = Path(__file__).parents[1] / "scripts" / "evaluate_rag_retrieval.py"
    spec = importlib.util.spec_from_file_location("rag_retrieval_eval_runner", runner_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    def fake_embed_documents(texts):
        return [
            [1.0, 0.0] if "relevant" in text else [0.0, 1.0]
            for text in texts
        ]

    async def fake_embed_query(_query):
        return [1.0, 0.0]

    monkeypatch.setattr(runner, "embed_documents_sync", fake_embed_documents)
    monkeypatch.setattr(runner, "embed_query", fake_embed_query)
    monkeypatch.setattr(
        runner,
        "get_embedding_index_identity",
        lambda: ("test", "test-model", "f" * 64),
    )

    report = runner.evaluate_dataset(
        {
            "schema_version": 1,
            "cases": [
                {
                    "id": "UNIT-001",
                    "domain": "programming",
                    "query": "find the relevant document",
                    "documents": [
                        {
                            "id": "relevant",
                            "relevance": 2,
                            "title": "Relevant",
                            "text": "This relevant document answers the query.",
                        },
                        {
                            "id": "negative",
                            "relevance": 0,
                            "title": "Negative",
                            "text": "This unrelated negative document talks about cooking.",
                        },
                    ],
                    "critical_failure": "Rank the irrelevant document first.",
                }
            ],
        },
        top_k=1,
    )

    assert report["embedding_provider"] == "test"
    assert report["embedding_model"] == "test-model"
    assert report["embedding_fingerprint"] == "f" * 64
    assert len(report["dataset_sha256"]) == 64
    assert report["case_count"] == 1
    assert report["cases"][0]["ranked_documents"][0]["id"] == "relevant"
    assert report["macro_average"]["recall_at_1"] == pytest.approx(1.0)
    assert report["macro_average"]["precision_at_1"] == pytest.approx(1.0)
    assert report["macro_average"]["ndcg_at_1"] == pytest.approx(1.0)
    assert report["macro_average"]["reciprocal_rank"] == pytest.approx(1.0)
    assert list(report["by_domain"]) == ["programming"]
    assert report["by_domain"]["programming"]["recall_at_2"] == pytest.approx(1.0)
    assert report["by_domain"]["programming"]["precision_at_2"] == pytest.approx(0.5)
    assert report["by_domain"]["programming"]["ndcg_at_2"] == pytest.approx(1.0)


def _load_rag_evaluation_runner():
    runner_path = Path(__file__).parents[1] / "scripts" / "evaluate_rag_retrieval.py"
    spec = importlib.util.spec_from_file_location("rag_retrieval_eval_runner_test", runner_path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner


def test_rag_validate_only_mode_never_calls_the_embedding_provider(monkeypatch, capsys):
    runner = _load_rag_evaluation_runner()

    def unexpected_provider_call(*_args, **_kwargs):
        pytest.fail("validate-only must not call an embedding provider")

    async def unexpected_async_provider_call(*_args, **_kwargs):
        pytest.fail("validate-only must not call an embedding provider")

    monkeypatch.setattr(runner.sys, "argv", ["evaluate_rag_retrieval.py", "--validate-only"])
    monkeypatch.setattr(runner, "embed_documents_sync", unexpected_provider_call)
    monkeypatch.setattr(runner, "embed_query", unexpected_async_provider_call)
    monkeypatch.setattr(runner, "get_embedding_index_identity", unexpected_provider_call)

    assert runner.main() == 0
    summary = json.loads(capsys.readouterr().out)

    assert summary["validation_only"] is True
    assert summary["live_embedding_requests_sent"] is False
    dataset = runner.load_dataset()
    expected_document_count = sum(len(case["documents"]) for case in dataset["cases"])
    assert summary["case_count"] == len(dataset["cases"])
    assert len(summary["dataset_sha256"]) == 64
    assert summary["document_count"] == expected_document_count
    assert len(summary["domain_counts"]) == 7
    assert sum(summary["relevance_grade_counts"].values()) == expected_document_count


def test_rag_dataset_validator_rejects_duplicate_document_ids():
    runner = _load_rag_evaluation_runner()
    dataset = runner.load_dataset()
    dataset["cases"][1]["documents"][0]["id"] = dataset["cases"][0]["documents"][0]["id"]

    with pytest.raises(ValueError, match="duplicate RAG document id"):
        runner.validate_dataset(dataset)


def _minimal_valid_rag_dataset():
    return {
        "schema_version": 1,
        "cases": [
            {
                "id": "UNIT-PREFLIGHT-001",
                "domain": "programming",
                "query": "find the relevant document",
                "documents": [
                    {
                        "id": "preflight-relevant",
                        "relevance": 2,
                        "title": "Relevant",
                        "text": "This relevant document answers the query.",
                    },
                    {
                        "id": "preflight-negative",
                        "relevance": 0,
                        "title": "Negative",
                        "text": "This unrelated negative document talks about cooking.",
                    },
                ],
                "critical_failure": "Rank the irrelevant document first.",
            }
        ],
    }


def test_evaluator_validates_dataset_before_provider_calls(monkeypatch):
    runner = _load_rag_evaluation_runner()

    def unexpected_call(*_args, **_kwargs):
        pytest.fail("Invalid benchmark data must be rejected before provider calls")

    async def unexpected_async_call(*_args, **_kwargs):
        pytest.fail("Invalid benchmark data must be rejected before provider calls")

    monkeypatch.setattr(runner, "embed_documents_sync", unexpected_call)
    monkeypatch.setattr(runner, "embed_query", unexpected_async_call)
    monkeypatch.setattr(runner, "get_embedding_index_identity", unexpected_call)

    with pytest.raises(ValueError, match="Each RAG case must contain"):
        runner.evaluate_dataset({"schema_version": 1, "cases": [{"id": "invalid"}]})


@pytest.mark.parametrize("top_k", [2, 3])
def test_evaluator_rejects_top_k_not_smaller_than_candidate_pool_before_provider_calls(monkeypatch, top_k):
    runner = _load_rag_evaluation_runner()

    def unexpected_call(*_args, **_kwargs):
        pytest.fail("Invalid top_k must be rejected before provider calls")

    async def unexpected_async_call(*_args, **_kwargs):
        pytest.fail("Invalid top_k must be rejected before provider calls")

    monkeypatch.setattr(runner, "embed_documents_sync", unexpected_call)
    monkeypatch.setattr(runner, "embed_query", unexpected_async_call)
    monkeypatch.setattr(runner, "get_embedding_index_identity", unexpected_call)

    with pytest.raises(ValueError, match="top_k must be smaller than the smallest candidate pool"):
        runner.evaluate_dataset(_minimal_valid_rag_dataset(), top_k=top_k)


def test_evaluator_checks_embedding_configuration_before_requests(monkeypatch):
    runner = _load_rag_evaluation_runner()
    events = []

    def fake_resolve_config():
        events.append("resolve_config")
        return ("test", "test-model", "f" * 64)

    def fake_embed_documents(texts):
        events.append("embed_documents")
        return [
            [1.0, 0.0] if "relevant" in text else [0.0, 1.0]
            for text in texts
        ]

    async def fake_embed_query(_query):
        events.append("embed_query")
        return [1.0, 0.0]

    monkeypatch.setattr(runner, "get_embedding_index_identity", fake_resolve_config)
    monkeypatch.setattr(runner, "embed_documents_sync", fake_embed_documents)
    monkeypatch.setattr(runner, "embed_query", fake_embed_query)

    report = runner.evaluate_dataset(_minimal_valid_rag_dataset(), top_k=2)

    assert events == ["resolve_config", "embed_documents", "embed_query"]
    assert report["embedding_model"] == "test-model"


def test_rag_default_mode_is_offline_and_never_calls_provider(monkeypatch, capsys):
    runner = _load_rag_evaluation_runner()

    def unexpected_provider_call(*_args, **_kwargs):
        pytest.fail("The default benchmark command must not call an embedding provider")

    async def unexpected_async_provider_call(*_args, **_kwargs):
        pytest.fail("The default benchmark command must not call an embedding provider")

    monkeypatch.setattr(runner.sys, "argv", ["evaluate_rag_retrieval.py"])
    monkeypatch.setattr(runner, "embed_documents_sync", unexpected_provider_call)
    monkeypatch.setattr(runner, "embed_query", unexpected_async_provider_call)
    monkeypatch.setattr(runner, "get_embedding_index_identity", unexpected_provider_call)

    assert runner.main() == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["validation_only"] is True
    assert summary["live_embedding_requests_sent"] is False
    assert summary["case_count"] == len(runner.load_dataset()["cases"])


def test_live_benchmark_runs_only_after_explicit_opt_in(monkeypatch, capsys):
    runner = _load_rag_evaluation_runner()
    seen = {}

    def fake_evaluate_dataset(dataset, top_k):
        seen["case_count"] = len(dataset["cases"])
        seen["top_k"] = top_k
        return {"benchmark": "test", "live_embedding_requests_sent": True}

    def unexpected_offline_summary(_dataset):
        pytest.fail("--run-live must not return an offline-only summary")

    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["evaluate_rag_retrieval.py", "--run-live", "--top-k", "2"],
    )
    monkeypatch.setattr(runner, "evaluate_dataset", fake_evaluate_dataset)
    monkeypatch.setattr(runner, "dataset_validation_summary", unexpected_offline_summary)

    assert runner.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert seen == {"case_count": len(runner.load_dataset()["cases"]), "top_k": 2}
    assert report["live_embedding_requests_sent"] is True


def test_live_and_validate_only_modes_cannot_be_combined(monkeypatch):
    runner = _load_rag_evaluation_runner()
    monkeypatch.setattr(
        runner.sys,
        "argv",
        ["evaluate_rag_retrieval.py", "--validate-only", "--run-live"],
    )

    with pytest.raises(SystemExit) as error:
        runner.main()

    assert error.value.code == 2


def test_benchmark_reports_when_an_irrelevant_document_ranks_first(monkeypatch):
    runner = _load_rag_evaluation_runner()

    def fake_embed_documents(texts):
        return [
            [1.0, 0.0] if "relevant" in text else [0.0, 1.0]
            for text in texts
        ]

    async def fake_embed_query(_query):
        return [0.0, 1.0]

    monkeypatch.setattr(runner, "embed_documents_sync", fake_embed_documents)
    monkeypatch.setattr(runner, "embed_query", fake_embed_query)
    monkeypatch.setattr(
        runner,
        "get_embedding_index_identity",
        lambda: ("test", "test-model", "f" * 64),
    )

    report = runner.evaluate_dataset(_minimal_valid_rag_dataset(), top_k=2)

    case = report["cases"][0]
    assert case["ranked_documents"][0]["id"] == "preflight-negative"
    assert case["top1_is_irrelevant"] is True
    assert case["first_relevant_rank"] == 2
    assert report["retrieval_diagnostics"]["top1_irrelevant_count"] == 1
    assert report["retrieval_diagnostics"]["top1_irrelevant_rate"] == pytest.approx(1.0)
    assert report["retrieval_diagnostics"]["mean_first_relevant_rank"] == pytest.approx(2.0)
    assert report["by_domain"]["programming"]["top1_irrelevant_count"] == 1
    assert report["by_domain"]["programming"]["top1_irrelevant_rate"] == pytest.approx(1.0)

def test_dataset_sha256_is_stable_and_changes_when_benchmark_content_changes():
    runner = _load_rag_evaluation_runner()
    original = {"schema_version": 1, "cases": [{"id": "one", "query": "test"}]}
    reordered = {"cases": [{"query": "test", "id": "one"}], "schema_version": 1}
    changed = {"schema_version": 1, "cases": [{"id": "one", "query": "changed"}]}

    assert runner.dataset_sha256(original) == runner.dataset_sha256(reordered)
    assert runner.dataset_sha256(original) != runner.dataset_sha256(changed)
    assert len(runner.dataset_sha256(original)) == 64


def test_evaluator_refuses_to_overwrite_benchmark_fixture(monkeypatch, capsys):
    runner = _load_rag_evaluation_runner()
    fixture_path = runner.FIXTURE_PATH
    original_content = fixture_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        runner.sys,
        "argv",
        [
            "evaluate_rag_retrieval.py",
            "--validate-only",
            "--output",
            str(fixture_path),
        ],
    )

    def unexpected_dataset_load():
        pytest.fail("The output path must be checked before loading or evaluating data")

    monkeypatch.setattr(runner, "load_dataset", unexpected_dataset_load)

    assert runner.main() == 2
    error = json.loads(capsys.readouterr().err)
    assert error["error"] == (
        "Output path must not overwrite the RAG evaluation fixture."
    )
    assert fixture_path.read_text(encoding="utf-8") == original_content
