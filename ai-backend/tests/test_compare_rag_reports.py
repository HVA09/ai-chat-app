"""Offline comparison tests for saved RAG retrieval reports."""
import importlib.util
import json
from pathlib import Path

import pytest

from app.services.rag_evaluation import score_ranked_results


def _load_comparator():
    script_path = Path(__file__).parents[1] / "scripts" / "compare_rag_reports.py"
    spec = importlib.util.spec_from_file_location("compare_rag_reports_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _report(
    *,
    dataset_sha256="a" * 64,
    fingerprint="b" * 64,
    model="test-model",
    irrelevant_case_ids=None,
    low_ndcg_case_ids=None,
    case_count=14,
):
    case_ids = [f"CASE-{index:03d}" for index in range(case_count)]
    if irrelevant_case_ids is None:
        irrelevant_case_ids = set(case_ids[: (case_count + 1) // 2])
    else:
        irrelevant_case_ids = set(irrelevant_case_ids)
    low_ndcg_case_ids = set(low_ndcg_case_ids or ())
    if not irrelevant_case_ids <= set(case_ids) or not low_ndcg_case_ids <= set(case_ids):
        raise ValueError("Unknown test case id.")
    if irrelevant_case_ids & low_ndcg_case_ids:
        raise ValueError("A case cannot use two mutually exclusive test rankings.")

    cases = []
    for index, case_id in enumerate(case_ids):
        documents_by_id = {
            f"{case_id}-relevant": {
                "id": f"{case_id}-relevant",
                "title": "Relevant document",
                "relevance": 2,
                "cosine_similarity": 0.99,
            },
            f"{case_id}-partial": {
                "id": f"{case_id}-partial",
                "title": "Partially relevant document",
                "relevance": 1,
                "cosine_similarity": 0.7,
            },
            f"{case_id}-partial-two": {
                "id": f"{case_id}-partial-two",
                "title": "Second partially relevant document",
                "relevance": 1,
                "cosine_similarity": 0.6,
            },
            f"{case_id}-negative": {
                "id": f"{case_id}-negative",
                "title": "Irrelevant document",
                "relevance": 0,
                "cosine_similarity": 0.2,
            },
            f"{case_id}-negative-two": {
                "id": f"{case_id}-negative-two",
                "title": "Second irrelevant document",
                "relevance": 0,
                "cosine_similarity": 0.1,
            },
        }
        if case_id in irrelevant_case_ids:
            ranking_order = [
                f"{case_id}-negative",
                f"{case_id}-relevant",
                f"{case_id}-partial",
                f"{case_id}-partial-two",
                f"{case_id}-negative-two",
            ]
        elif case_id in low_ndcg_case_ids:
            ranking_order = [
                f"{case_id}-partial",
                f"{case_id}-negative",
                f"{case_id}-partial-two",
                f"{case_id}-relevant",
                f"{case_id}-negative-two",
            ]
        else:
            ranking_order = [
                f"{case_id}-relevant",
                f"{case_id}-partial",
                f"{case_id}-partial-two",
                f"{case_id}-negative",
                f"{case_id}-negative-two",
            ]
        ranked_documents = [dict(documents_by_id[document_id]) for document_id in ranking_order]
        # Keep synthetic report rows structurally realistic: scores must follow
        # the reported ranking order even when relevance is intentionally poor.
        for rank, document in enumerate(ranked_documents):
            document["cosine_similarity"] = round(0.99 - rank * 0.1, 6)
        relevance_by_id = {
            document_id: document["relevance"]
            for document_id, document in documents_by_id.items()
        }
        metrics = score_ranked_results(ranking_order, relevance_by_id, k=3)
        first_relevant_rank = next(
            rank
            for rank, document in enumerate(ranked_documents, start=1)
            if document["relevance"] > 0
        )
        top1_is_irrelevant = ranked_documents[0]["relevance"] == 0
        cases.append(
            {
                "case_id": case_id,
                "domain": "programming" if index < (case_count + 1) // 2 else "networking",
                "query": f"Test query {case_id}",
                "metrics": metrics,
                "top1_is_irrelevant": top1_is_irrelevant,
                "first_relevant_rank": first_relevant_rank,
                "ranked_documents": ranked_documents,
                "critical_failure": "Rank the irrelevant document first.",
            }
        )

    metric_names = set(cases[0]["metrics"])
    macro_average = {
        metric: round(sum(case["metrics"][metric] for case in cases) / len(cases), 4)
        for metric in metric_names
    }
    by_domain = {}
    for domain in sorted({case["domain"] for case in cases}):
        domain_cases = [case for case in cases if case["domain"] == domain]
        domain_bad_count = sum(case["top1_is_irrelevant"] for case in domain_cases)
        domain_summary = {
            metric: round(
                sum(case["metrics"][metric] for case in domain_cases) / len(domain_cases),
                4,
            )
            for metric in metric_names
        }
        domain_summary.update(
            {
                "top1_irrelevant_count": domain_bad_count,
                "top1_irrelevant_rate": round(domain_bad_count / len(domain_cases), 4),
                "mean_first_relevant_rank": round(
                    sum(case["first_relevant_rank"] for case in domain_cases)
                    / len(domain_cases),
                    4,
                ),
            }
        )
        by_domain[domain] = domain_summary

    bad_count = sum(case["top1_is_irrelevant"] for case in cases)
    return {
        "benchmark": "rag-retrieval-eval-v1",
        "dataset_sha256": dataset_sha256,
        "embedding_provider": "test-provider",
        "embedding_model": model,
        "embedding_fingerprint": fingerprint,
        "top_k": 3,
        "case_count": len(cases),
        "macro_average": macro_average,
        "retrieval_diagnostics": {
            "top1_irrelevant_count": bad_count,
            "top1_irrelevant_rate": round(bad_count / len(cases), 4),
            "mean_first_relevant_rank": round(
                sum(case["first_relevant_rank"] for case in cases) / len(cases),
                4,
            ),
        },
        "by_domain": by_domain,
        "cases": cases,
    }


def test_report_comparison_marks_improvements_and_regressions():
    comparator = _load_comparator()
    baseline = _report()
    candidate = _report(
        fingerprint="c" * 64,
        model="candidate-model",
        irrelevant_case_ids={"CASE-013"},
        low_ndcg_case_ids={
            "CASE-001", "CASE-002", "CASE-003", "CASE-004", "CASE-005"
        },
    )

    result = comparator.compare_reports(baseline, candidate)

    assert result["embedding_fingerprint_changed"] is True
    assert result["macro_average"]["recall_at_3"]["status"] == "improved"
    assert result["macro_average"]["precision_at_3"]["status"] == "improved"
    assert result["macro_average"]["ndcg_at_3"]["status"] == "regressed"
    assert result["macro_average"]["reciprocal_rank"]["status"] == "improved"
    assert result["retrieval_diagnostics"]["top1_irrelevant_rate"]["status"] == "improved"
    assert result["retrieval_diagnostics"]["mean_first_relevant_rank"]["status"] == "improved"
    assert result["by_domain"]["programming"]["ndcg_at_3"]["status"] == "regressed"
    assert result["comparison_counts"]["regressed"] > 0
    assert result["comparison_counts"]["improved"] > 0
    assert "by_case" in result
    assert result["by_case"]["CASE-010"]["top1_irrelevant"]["status"] == "unchanged"


def test_comparator_rejects_different_dataset_or_run_settings():
    comparator = _load_comparator()
    with pytest.raises(ValueError, match="different benchmark datasets"):
        comparator.compare_reports(
            _report(),
            _report(dataset_sha256="d" * 64),
        )

    candidate = _report()
    candidate["top_k"] = 2
    with pytest.raises(ValueError, match="different top_k"):
        comparator.compare_reports(_report(), candidate)

    candidate = _report(case_count=13)
    with pytest.raises(ValueError, match="different case_count"):
        comparator.compare_reports(_report(), candidate)


def test_comparator_rejects_malformed_report_without_exposing_secrets():
    comparator = _load_comparator()
    candidate = _report()
    candidate["embedding_fingerprint"] = "API_KEY_DO_NOT_EXPOSE"

    with pytest.raises(ValueError, match="invalid embedding_fingerprint"):
        comparator.compare_reports(_report(), candidate)


def test_cli_reads_local_reports_and_writes_comparison(tmp_path, monkeypatch, capsys):
    comparator = _load_comparator()
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    output_path = tmp_path / "comparison.json"
    baseline_path.write_text(json.dumps(_report()), encoding="utf-8")
    candidate_path.write_text(
        json.dumps(_report(fingerprint="c" * 64, irrelevant_case_ids=set())),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        comparator.sys,
        "argv",
        [
            "compare_rag_reports.py",
            str(baseline_path),
            str(candidate_path),
            "--output",
            str(output_path),
        ],
    )

    assert comparator.main() == 0
    assert "written" in capsys.readouterr().out
    result = json.loads(output_path.read_text(encoding="utf-8"))
    assert result["macro_average"]["recall_at_3"]["delta_candidate_minus_baseline"] == pytest.approx(0.1667)


def test_cli_will_not_overwrite_an_input_report(tmp_path, monkeypatch, capsys):
    comparator = _load_comparator()
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    baseline_path.write_text(json.dumps(_report()), encoding="utf-8")
    candidate_path.write_text(json.dumps(_report(fingerprint="c" * 64)), encoding="utf-8")
    original_baseline = baseline_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        comparator.sys,
        "argv",
        [
            "compare_rag_reports.py",
            str(baseline_path),
            str(candidate_path),
            "--output",
            str(baseline_path),
        ],
    )

    assert comparator.main() == 2
    assert json.loads(capsys.readouterr().err)["error"] == (
        "Output path must not overwrite either input report."
    )
    assert baseline_path.read_text(encoding="utf-8") == original_baseline


def test_comparator_surfaces_case_level_regression_hidden_by_better_macro_metrics():
    comparator = _load_comparator()
    baseline = _report()
    candidate = _report(
        fingerprint="c" * 64,
        model="candidate-model",
        irrelevant_case_ids={"CASE-000", "CASE-010"},
        low_ndcg_case_ids={"CASE-001"},
    )

    result = comparator.compare_reports(baseline, candidate)

    assert result["macro_average"]["recall_at_3"]["status"] == "improved"
    assert result["retrieval_diagnostics"]["top1_irrelevant_rate"]["status"] == "improved"
    case = result["by_case"]["CASE-010"]
    assert case["top1_irrelevant"]["status"] == "regressed"
    assert case["baseline_top1_document"]["relevance"] == 2
    assert case["candidate_top1_document"]["relevance"] == 0
    assert case["critical_failure"] == "Rank the irrelevant document first."
    assert result["cases_with_top1_regression"] == [
        {
            "case_id": "CASE-010",
            "domain": "networking",
            "critical_failure": "Rank the irrelevant document first.",
            "baseline_top1_document": {
                "id": "CASE-010-relevant",
                "title": "Relevant document",
                "relevance": 2,
            },
            "candidate_top1_document": {
                "id": "CASE-010-negative",
                "title": "Irrelevant document",
                "relevance": 0,
            },
        }
    ]
    assert result["case_comparison_counts"]["mixed"] >= 1


def test_comparator_rejects_inconsistent_case_level_rankings():
    comparator = _load_comparator()

    bad_rank = _report()
    bad_rank["cases"][0]["first_relevant_rank"] = 3
    with pytest.raises(ValueError, match="inconsistent first_relevant_rank"):
        comparator.compare_reports(_report(), bad_rank)

    bad_flag = _report()
    bad_flag["cases"][0]["top1_is_irrelevant"] = not bad_flag["cases"][0]["top1_is_irrelevant"]
    with pytest.raises(ValueError, match="inconsistent top1_is_irrelevant"):
        comparator.compare_reports(_report(), bad_flag)



def test_comparator_rejects_inconsistent_metric_aggregates_and_out_of_range_values():
    comparator = _load_comparator()

    bad_case_metric = _report()
    bad_case_metric["cases"][0]["metrics"]["recall_at_3"] = 0.99
    with pytest.raises(ValueError, match="macro_average.*case-level metric averages"):
        comparator.compare_reports(_report(), bad_case_metric)

    bad_domain_metric = _report()
    bad_domain_metric["by_domain"]["programming"]["ndcg_at_3"] = 0.1
    with pytest.raises(ValueError, match="by_domain.*case-level metric averages"):
        comparator.compare_reports(_report(), bad_domain_metric)

    out_of_range = _report()
    out_of_range["macro_average"]["precision_at_3"] = 1.2
    with pytest.raises(ValueError, match="between 0 and 1"):
        comparator.compare_reports(_report(), out_of_range)


def test_comparator_rejects_missing_case_rows():
    comparator = _load_comparator()
    incomplete = _report()
    incomplete["cases"].pop()

    with pytest.raises(ValueError, match="exactly case_count entries"):
        comparator.compare_reports(_report(), incomplete)


def test_comparator_rejects_different_ranked_document_sets_even_with_same_hash():
    comparator = _load_comparator()
    baseline = _report()
    candidate = _report(fingerprint="c" * 64)
    candidate["cases"][0]["ranked_documents"][1]["id"] = "substituted-document"

    with pytest.raises(ValueError, match="rank different document ids"):
        comparator.compare_reports(baseline, candidate)


def test_comparator_rejects_changed_relevance_labels_for_same_corpus():
    comparator = _load_comparator()
    baseline = _report()
    candidate = _report(fingerprint="c" * 64)
    candidate["cases"][0]["ranked_documents"][2]["relevance"] = 0

    with pytest.raises(ValueError, match="different document labels"):
        comparator.compare_reports(baseline, candidate)


def test_report_validator_rejects_document_ids_reused_across_cases():
    comparator = _load_comparator()
    malformed = _report()
    malformed["cases"][1]["ranked_documents"][0]["id"] = (
        malformed["cases"][0]["ranked_documents"][0]["id"]
    )

    with pytest.raises(ValueError, match="duplicate ranked document id across cases"):
        comparator.compare_reports(_report(), malformed)


def test_report_validator_rejects_cosine_similarity_outside_valid_range():
    comparator = _load_comparator()
    malformed = _report()
    malformed["cases"][0]["ranked_documents"][0]["cosine_similarity"] = 3.5

    with pytest.raises(ValueError, match="cosine similarity outside"):
        comparator.compare_reports(_report(), malformed)

def test_comparator_rejects_metrics_that_do_not_match_ranked_document_order():
    comparator = _load_comparator()
    candidate = _report()

    # Keep macro and per-domain summaries consistent with the tampered case rows;
    # the validator must independently recompute metrics from the ranked documents.
    for case in candidate["cases"]:
        case["metrics"]["recall_at_3"] = 0.99
    candidate["macro_average"]["recall_at_3"] = 0.99
    for domain in candidate["by_domain"].values():
        domain["recall_at_3"] = 0.99

    with pytest.raises(ValueError, match="does not match its ranked document order"):
        comparator.compare_reports(_report(), candidate)


def test_comparator_rejects_metric_names_that_do_not_match_top_k():
    comparator = _load_comparator()
    baseline = _report()
    candidate = _report()
    baseline["top_k"] = 2
    candidate["top_k"] = 2

    with pytest.raises(ValueError, match="metric names do not match top_k=2"):
        comparator.compare_reports(baseline, candidate)


def test_report_validator_rejects_cosine_scores_that_conflict_with_rank_order():
    comparator = _load_comparator()
    malformed = _report()
    malformed["cases"][0]["ranked_documents"][1]["cosine_similarity"] = 1.0

    with pytest.raises(ValueError, match="not sorted by descending cosine similarity"):
        comparator.compare_reports(_report(), malformed)
