"""Offline comparison tests for saved RAG retrieval reports."""
import importlib.util
import json
from pathlib import Path

import pytest


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
    recall=0.5,
    precision=0.5,
    ndcg=0.7,
    reciprocal_rank=0.5,
    top1_irrelevant_rate=0.5,
    irrelevant_case_ids=None,
    case_count=14,
):
    metrics = {
        "recall_at_3": recall,
        "precision_at_3": precision,
        "ndcg_at_3": ndcg,
        "reciprocal_rank": reciprocal_rank,
    }
    case_ids = [f"CASE-{index:03d}" for index in range(case_count)]
    if irrelevant_case_ids is None:
        bad_count = round(top1_irrelevant_rate * len(case_ids))
        irrelevant_case_ids = set(case_ids[:bad_count])
    else:
        irrelevant_case_ids = set(irrelevant_case_ids)
        if not irrelevant_case_ids <= set(case_ids):
            raise ValueError("Unknown test case id.")

    cases = []
    for index, case_id in enumerate(case_ids):
        top1_is_irrelevant = case_id in irrelevant_case_ids
        if top1_is_irrelevant:
            ranked_documents = [
                {
                    "id": f"{case_id}-negative",
                    "title": "Irrelevant document",
                    "relevance": 0,
                    "cosine_similarity": 0.99,
                },
                {
                    "id": f"{case_id}-relevant",
                    "title": "Relevant document",
                    "relevance": 2,
                    "cosine_similarity": 0.98,
                },
                {
                    "id": f"{case_id}-partial",
                    "title": "Partially relevant document",
                    "relevance": 1,
                    "cosine_similarity": 0.2,
                },
            ]
        else:
            ranked_documents = [
                {
                    "id": f"{case_id}-relevant",
                    "title": "Relevant document",
                    "relevance": 2,
                    "cosine_similarity": 0.99,
                },
                {
                    "id": f"{case_id}-partial",
                    "title": "Partially relevant document",
                    "relevance": 1,
                    "cosine_similarity": 0.5,
                },
                {
                    "id": f"{case_id}-negative",
                    "title": "Irrelevant document",
                    "relevance": 0,
                    "cosine_similarity": 0.2,
                },
            ]
        cases.append(
            {
                "case_id": case_id,
                "domain": "programming" if index < (case_count + 1) // 2 else "networking",
                "query": f"Test query {case_id}",
                "metrics": dict(metrics),
                "top1_is_irrelevant": top1_is_irrelevant,
                "first_relevant_rank": 2 if top1_is_irrelevant else 1,
                "ranked_documents": ranked_documents,
                "critical_failure": "Rank the irrelevant document first.",
            }
        )

    by_domain = {}
    for domain in ("programming", "networking"):
        domain_cases = [case for case in cases if case["domain"] == domain]
        domain_bad_count = sum(case["top1_is_irrelevant"] for case in domain_cases)
        by_domain[domain] = {
            **metrics,
            "top1_irrelevant_count": domain_bad_count,
            "top1_irrelevant_rate": round(domain_bad_count / len(domain_cases), 4),
            "mean_first_relevant_rank": round(
                sum(case["first_relevant_rank"] for case in domain_cases)
                / len(domain_cases),
                4,
            ),
        }

    bad_count = sum(case["top1_is_irrelevant"] for case in cases)
    return {
        "benchmark": "rag-retrieval-eval-v1",
        "dataset_sha256": dataset_sha256,
        "embedding_provider": "test-provider",
        "embedding_model": model,
        "embedding_fingerprint": fingerprint,
        "top_k": 3,
        "case_count": len(cases),
        "macro_average": metrics,
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
        recall=0.75,
        precision=0.4,
        ndcg=0.6,
        reciprocal_rank=0.8,
        top1_irrelevant_rate=0.1,
    )

    result = comparator.compare_reports(baseline, candidate)

    assert result["embedding_fingerprint_changed"] is True
    assert result["macro_average"]["recall_at_3"]["status"] == "improved"
    assert result["macro_average"]["precision_at_3"]["status"] == "regressed"
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
        json.dumps(_report(fingerprint="c" * 64, recall=0.8)),
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
    assert result["macro_average"]["recall_at_3"]["delta_candidate_minus_baseline"] == pytest.approx(0.3)


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
        recall=0.75,
        precision=0.6,
        ndcg=0.8,
        reciprocal_rank=0.8,
        top1_irrelevant_rate=2 / 14,
        irrelevant_case_ids={"CASE-000", "CASE-010"},
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
