"""Offline integrity checks for the AI specialist evaluation dataset."""

import json
from collections import Counter
from pathlib import Path


EVALUATION_FILE = (
    Path(__file__).parent / "fixtures" / "ai_specialist_eval_cases.json"
)
REQUIRED_FIELDS = {
    "id",
    "domain",
    "level",
    "task_type",
    "prompt",
    "evaluation_criteria",
    "critical_failures",
    "expected_evidence",
}
EXPECTED_CORE_DOMAINS = {
    "networking",
    "linux",
    "programming",
    "cybersecurity",
    "cloud",
    "teaching",
    "cross_domain",
}


def _load_evaluation_cases():
    with EVALUATION_FILE.open(encoding="utf-8") as fixture:
        dataset = json.load(fixture)
    assert dataset["schema_version"] == 1
    assert isinstance(dataset.get("cases"), list)
    return dataset["cases"]


def test_evaluation_dataset_has_unique_ids_and_complete_fields():
    cases = _load_evaluation_cases()
    assert cases, "The evaluation dataset must not be empty"

    case_ids = [case.get("id") for case in cases]
    assert all(isinstance(case_id, str) and case_id for case_id in case_ids)
    assert len(case_ids) == len(set(case_ids)), "Evaluation case IDs must be unique"

    for case in cases:
        assert REQUIRED_FIELDS <= case.keys(), case.get("id")
        assert case["domain"] in EXPECTED_CORE_DOMAINS, case["id"]
        assert case["level"] in {"beginner", "intermediate", "advanced"}, case["id"]
        assert isinstance(case["prompt"], str) and len(case["prompt"].strip()) >= 30
        assert isinstance(case["evaluation_criteria"], list)
        assert case["evaluation_criteria"], case["id"]
        assert isinstance(case["critical_failures"], list)
        assert case["critical_failures"], case["id"]
        assert isinstance(case["expected_evidence"], str)
        assert case["expected_evidence"].strip(), case["id"]


def test_evaluation_dataset_covers_all_domains_and_integrated_tasks():
    cases = _load_evaluation_cases()
    counts = Counter(case["domain"] for case in cases)

    assert EXPECTED_CORE_DOMAINS <= counts.keys()
    for domain in EXPECTED_CORE_DOMAINS - {"cross_domain"}:
        assert counts[domain] >= 5, f"Expected at least five {domain} cases"

    assert counts["cross_domain"] >= 5
