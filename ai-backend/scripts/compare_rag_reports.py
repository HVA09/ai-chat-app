"""Compare two saved RAG benchmark reports offline, without provider requests.

Example:
    python scripts/compare_rag_reports.py reports/baseline.json reports/candidate.json

Both reports must use the same benchmark dataset, top-k, case count, and domains.
This tool only reads the report files and does not call AI providers or databases.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

BENCHMARK_NAME = "rag-retrieval-eval-v1"
COMPARISON_NAME = "rag-retrieval-comparison-v1"
EPSILON = 1e-6
HIGHER_IS_BETTER = {
    "recall_at_",
    "precision_at_",
    "ndcg_at_",
    "reciprocal_rank",
}
LOWER_IS_BETTER = {
    "top1_irrelevant_rate",
    "mean_first_relevant_rank",
}


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number.")
    return number


def _validate_report(report: Any, label: str) -> dict[str, Any]:
    if not isinstance(report, dict) or report.get("benchmark") != BENCHMARK_NAME:
        raise ValueError(f"{label} is not a {BENCHMARK_NAME} report.")

    digest = report.get("dataset_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(
        char not in "0123456789abcdef" for char in digest.lower()
    ):
        raise ValueError(f"{label} has an invalid dataset_sha256.")
    fingerprint = report.get("embedding_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(
        char not in "0123456789abcdef" for char in fingerprint.lower()
    ):
        raise ValueError(f"{label} has an invalid embedding_fingerprint.")

    if (
        isinstance(report.get("case_count"), bool)
        or not isinstance(report.get("case_count"), int)
        or report["case_count"] < 1
    ):
        raise ValueError(f"{label} has an invalid case_count.")
    if (
        isinstance(report.get("top_k"), bool)
        or not isinstance(report.get("top_k"), int)
        or report["top_k"] < 1
    ):
        raise ValueError(f"{label} has an invalid top_k.")

    metrics = report.get("macro_average")
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError(f"{label} is missing macro_average metrics.")
    for name, value in metrics.items():
        _finite_number(value, f"{label}.macro_average.{name}")
        _direction(name)

    by_domain = report.get("by_domain")
    if not isinstance(by_domain, dict) or not by_domain:
        raise ValueError(f"{label} is missing by_domain metrics.")
    for domain, values in by_domain.items():
        if not isinstance(domain, str) or not domain or not isinstance(values, dict):
            raise ValueError(f"{label}.by_domain contains an invalid domain entry.")
        if not set(metrics) <= set(values):
            raise ValueError(f"{label}.by_domain.{domain} is missing ranking metrics.")
        for name, value in values.items():
            if name in metrics:
                _finite_number(value, f"{label}.by_domain.{domain}.{name}")
            elif name in LOWER_IS_BETTER:
                _finite_number(value, f"{label}.by_domain.{domain}.{name}")
            elif name == "top1_irrelevant_count":
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"{label}.by_domain.{domain}.{name} must be a non-negative integer.")
            else:
                raise ValueError(f"{label}.by_domain.{domain} contains unsupported metric {name}.")

    cases = report.get("cases")
    if not isinstance(cases, list) or len(cases) != report["case_count"]:
        raise ValueError(f"{label}.cases must contain exactly case_count entries.")

    case_ids: set[str] = set()
    seen_document_ids_by_case: set[tuple[str, str]] = set()
    cases_by_domain: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError(f"{label}.cases contains a non-object entry.")
        required = {
            "case_id",
            "domain",
            "metrics",
            "top1_is_irrelevant",
            "first_relevant_rank",
            "ranked_documents",
            "critical_failure",
        }
        if not required <= set(case):
            raise ValueError(f"{label}.cases contains an incomplete case entry.")

        case_id = case["case_id"]
        domain = case["domain"]
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            raise ValueError(f"{label} contains a missing or duplicate case_id.")
        if not isinstance(domain, str) or domain not in by_domain:
            raise ValueError(f"{label} case {case_id} has an unknown domain.")
        case_ids.add(case_id)
        cases_by_domain.setdefault(domain, []).append(case)

        case_metrics = case["metrics"]
        if not isinstance(case_metrics, dict) or set(case_metrics) != set(metrics):
            raise ValueError(f"{label} case {case_id} has an incompatible metric set.")
        for name, value in case_metrics.items():
            _finite_number(value, f"{label}.cases.{case_id}.metrics.{name}")

        if not isinstance(case["top1_is_irrelevant"], bool):
            raise ValueError(f"{label} case {case_id} has an invalid top1_is_irrelevant.")
        first_rank = case["first_relevant_rank"]
        if isinstance(first_rank, bool) or not isinstance(first_rank, int) or first_rank < 1:
            raise ValueError(f"{label} case {case_id} has an invalid first_relevant_rank.")
        if not isinstance(case["critical_failure"], str) or not case["critical_failure"].strip():
            raise ValueError(f"{label} case {case_id} is missing critical_failure guidance.")

        ranked = case["ranked_documents"]
        if not isinstance(ranked, list) or not ranked:
            raise ValueError(f"{label} case {case_id} has no ranked documents.")
        ranked_ids: set[str] = set()
        actual_first_relevant_rank = None
        for rank, document in enumerate(ranked, start=1):
            if not isinstance(document, dict):
                raise ValueError(f"{label} case {case_id} contains an invalid ranked document.")
            document_id = document.get("id")
            if not isinstance(document_id, str) or not document_id or document_id in ranked_ids:
                raise ValueError(f"{label} case {case_id} has a missing or duplicate ranked document id.")
            ranked_ids.add(document_id)
            relevance = document.get("relevance")
            if (
                isinstance(relevance, bool)
                or not isinstance(relevance, int)
                or relevance not in {0, 1, 2}
            ):
                raise ValueError(f"{label} case {case_id} has an invalid relevance grade.")
            if not isinstance(document.get("title"), str) or not document["title"].strip():
                raise ValueError(f"{label} case {case_id} has a ranked document without a title.")
            _finite_number(
                document.get("cosine_similarity"),
                f"{label}.cases.{case_id}.ranked_documents.{rank}.cosine_similarity",
            )
            if relevance > 0 and actual_first_relevant_rank is None:
                actual_first_relevant_rank = rank
            seen_document_ids_by_case.add((case_id, document_id))

        if actual_first_relevant_rank is None or actual_first_relevant_rank != first_rank:
            raise ValueError(f"{label} case {case_id} has inconsistent first_relevant_rank.")
        top1_is_irrelevant = ranked[0]["relevance"] == 0
        if case["top1_is_irrelevant"] != top1_is_irrelevant:
            raise ValueError(f"{label} case {case_id} has inconsistent top1_is_irrelevant.")

    if set(cases_by_domain) != set(by_domain):
        raise ValueError(f"{label} has inconsistent case and by_domain coverage.")

    diagnostics = report.get("retrieval_diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError(f"{label} is missing retrieval_diagnostics.")
    for name in LOWER_IS_BETTER:
        if name not in diagnostics:
            raise ValueError(f"{label}.retrieval_diagnostics is missing {name}.")
        _finite_number(diagnostics[name], f"{label}.retrieval_diagnostics.{name}")
    bad_count = sum(case["top1_is_irrelevant"] for case in cases)
    expected_rate = bad_count / len(cases)
    expected_first_rank = sum(case["first_relevant_rank"] for case in cases) / len(cases)
    if (
        isinstance(diagnostics.get("top1_irrelevant_count"), bool)
        or diagnostics.get("top1_irrelevant_count") != bad_count
    ):
        raise ValueError(f"{label}.retrieval_diagnostics has inconsistent top1_irrelevant_count.")
    if abs(float(diagnostics["top1_irrelevant_rate"]) - expected_rate) > 0.00011:
        raise ValueError(f"{label}.retrieval_diagnostics has inconsistent top1_irrelevant_rate.")
    if abs(float(diagnostics["mean_first_relevant_rank"]) - expected_first_rank) > 0.00011:
        raise ValueError(f"{label}.retrieval_diagnostics has inconsistent mean_first_relevant_rank.")

    for domain, domain_cases in cases_by_domain.items():
        values = by_domain[domain]
        domain_bad_count = sum(case["top1_is_irrelevant"] for case in domain_cases)
        domain_rate = domain_bad_count / len(domain_cases)
        domain_first_rank = sum(case["first_relevant_rank"] for case in domain_cases) / len(domain_cases)
        if values.get("top1_irrelevant_count") != domain_bad_count:
            raise ValueError(f"{label}.by_domain.{domain} has inconsistent top1_irrelevant_count.")
        if abs(float(values["top1_irrelevant_rate"]) - domain_rate) > 0.00011:
            raise ValueError(f"{label}.by_domain.{domain} has inconsistent top1_irrelevant_rate.")
        if abs(float(values["mean_first_relevant_rank"]) - domain_first_rank) > 0.00011:
            raise ValueError(f"{label}.by_domain.{domain} has inconsistent mean_first_relevant_rank.")

    return report

def _direction(metric_name: str) -> str:
    if metric_name in LOWER_IS_BETTER:
        return "lower_is_better"
    if metric_name.startswith(tuple(HIGHER_IS_BETTER)):
        return "higher_is_better"
    raise ValueError(f"Unsupported metric in RAG report: {metric_name}")


def _compare_value(baseline_value: Any, candidate_value: Any, direction: str) -> dict[str, Any]:
    baseline = _finite_number(baseline_value, "baseline value")
    candidate = _finite_number(candidate_value, "candidate value")
    delta = candidate - baseline
    normalized_delta = delta if direction == "higher_is_better" else -delta
    if normalized_delta > EPSILON:
        status = "improved"
    elif normalized_delta < -EPSILON:
        status = "regressed"
    else:
        status = "unchanged"
    return {
        "baseline": round(baseline, 6),
        "candidate": round(candidate, 6),
        "delta_candidate_minus_baseline": round(delta, 6),
        "direction": direction,
        "status": status,
    }


def compare_reports(baseline_report: Any, candidate_report: Any) -> dict[str, Any]:
    """Compare two reports only when both describe the same benchmark corpus."""
    baseline = _validate_report(baseline_report, "baseline")
    candidate = _validate_report(candidate_report, "candidate")

    if baseline["dataset_sha256"] != candidate["dataset_sha256"]:
        raise ValueError(
            "Reports use different benchmark datasets (dataset_sha256 mismatch); "
            "re-run both reports on the same dataset before comparing."
        )
    for field in ("case_count", "top_k"):
        if baseline[field] != candidate[field]:
            raise ValueError(f"Reports have different {field}; comparison is not valid.")
    if set(baseline["macro_average"]) != set(candidate["macro_average"]):
        raise ValueError("Reports contain different macro-average metric sets.")
    if set(baseline["by_domain"]) != set(candidate["by_domain"]):
        raise ValueError("Reports contain different domain sets.")

    metric_comparisons: dict[str, Any] = {}
    for metric in sorted(baseline["macro_average"]):
        direction = _direction(metric)
        metric_comparisons[metric] = _compare_value(
            baseline["macro_average"][metric],
            candidate["macro_average"][metric],
            direction,
        )

    diagnostics_comparisons: dict[str, Any] = {}
    for metric in sorted(LOWER_IS_BETTER):
        diagnostics_comparisons[metric] = _compare_value(
            baseline["retrieval_diagnostics"][metric],
            candidate["retrieval_diagnostics"][metric],
            "lower_is_better",
        )

    domain_comparisons: dict[str, Any] = {}
    for domain in sorted(baseline["by_domain"]):
        base_domain = baseline["by_domain"][domain]
        cand_domain = candidate["by_domain"][domain]
        if not isinstance(base_domain, dict) or not isinstance(cand_domain, dict):
            raise ValueError(f"Invalid metric details for domain {domain}.")
        expected_metrics = set(baseline["macro_average"]) | LOWER_IS_BETTER
        if not expected_metrics <= set(base_domain) or not expected_metrics <= set(cand_domain):
            raise ValueError(f"Missing metric values for domain {domain}.")
        domain_comparisons[domain] = {
            metric: _compare_value(
                base_domain[metric],
                cand_domain[metric],
                _direction(metric),
            )
            for metric in sorted(expected_metrics)
        }

    all_comparisons = [
        *metric_comparisons.values(),
        *diagnostics_comparisons.values(),
        *(value for domain in domain_comparisons.values() for value in domain.values()),
    ]
    improved = sum(item["status"] == "improved" for item in all_comparisons)
    regressed = sum(item["status"] == "regressed" for item in all_comparisons)
    unchanged = sum(item["status"] == "unchanged" for item in all_comparisons)

    return {
        "comparison": COMPARISON_NAME,
        "dataset_sha256": baseline["dataset_sha256"],
        "case_count": baseline["case_count"],
        "top_k": baseline["top_k"],
        "baseline_embedding": {
            "provider": baseline.get("embedding_provider"),
            "model": baseline.get("embedding_model"),
            "fingerprint": baseline["embedding_fingerprint"],
        },
        "candidate_embedding": {
            "provider": candidate.get("embedding_provider"),
            "model": candidate.get("embedding_model"),
            "fingerprint": candidate["embedding_fingerprint"],
        },
        "embedding_fingerprint_changed": (
            baseline["embedding_fingerprint"] != candidate["embedding_fingerprint"]
        ),
        "macro_average": metric_comparisons,
        "retrieval_diagnostics": diagnostics_comparisons,
        "by_domain": domain_comparisons,
        "comparison_counts": {
            "improved": improved,
            "regressed": regressed,
            "unchanged": unchanged,
        },
        "interpretation": (
            "Metric deltas are descriptive, not an automatic release decision. "
            "Review critical retrieval failures, per-domain results, citation quality, "
            "access controls, and answer quality before changing production."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, help="Path to the saved baseline JSON report.")
    parser.add_argument("candidate", type=Path, help="Path to the saved candidate JSON report.")
    parser.add_argument("--output", type=Path, help="Optional path to write the comparison JSON.")
    args = parser.parse_args()

    try:
        input_paths = {args.baseline.resolve(), args.candidate.resolve()}
        if args.output and args.output.resolve() in input_paths:
            raise ValueError("Output path must not overwrite either input report.")
        with args.baseline.open(encoding="utf-8") as source:
            baseline = json.load(source)
        with args.candidate.open(encoding="utf-8") as source:
            candidate = json.load(source)
        comparison = compare_reports(baseline, candidate)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    rendered = json.dumps(comparison, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"RAG comparison report written to {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
