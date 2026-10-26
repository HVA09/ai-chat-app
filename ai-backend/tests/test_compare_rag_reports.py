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
    mean_first_relevant_rank=2.0,
):
    metrics = {
        "recall_at_3": recall,
        "precision_at_3": precision,
        "ndcg_at_3": ndcg,
        "reciprocal_rank": reciprocal_rank,
    }
    domain_metrics = {
        **metrics,
        "top1_irrelevant_count": 1,
        "top1_irrelevant_rate": top1_irrelevant_rate,
        "mean_first_relevant_rank": mean_first_relevant_rank,
    }
    return {
        "benchmark": "rag-retrieval-eval-v1",
        "dataset_sha256": dataset_sha256,
        "embedding_provider": "test-provider",
        "embedding_model": model,
        "embedding_fingerprint": fingerprint,
        "top_k": 3,
        "case_count": 14,
        "macro_average": metrics,
        "retrieval_diagnostics": {
            "top1_irrelevant_count": 7,
            "top1_irrelevant_rate": top1_irrelevant_rate,
            "mean_first_relevant_rank": mean_first_relevant_rank,
        },
        "by_domain": {
            "programming": domain_metrics,
            "networking": domain_metrics,
        },
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
        mean_first_relevant_rank=1.25,
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

    candidate = _report()
    candidate["case_count"] = 13
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
