"""Offline tests for citation-ID consistency checks."""

import pytest

from app.services.citation_evaluation import evaluate_answer_citations


def test_answer_citation_report_counts_valid_and_unsupported_ids():
    report = evaluate_answer_citations(
        "The network interface command is documented here [S1]. "
        "A second source agrees [W2]. See also [S1]. This claim cites [S99].",
        [
            {"id": "S1", "filename": "linux.txt"},
            {"id": "W2", "filename": "docs", "kind": "web"},
        ],
    )

    assert report == {
        "citation_count": 4,
        "valid_citation_count": 3,
        "unsupported_citation_count": 1,
        "unsupported_citation_ids": ["S99"],
        "available_source_count": 2,
        "cited_source_ids": ["S1", "W2"],
        "uncited_source_ids": [],
        "citation_precision": 0.75,
        "source_coverage": 1.0,
    }


def test_no_citations_is_distinguished_from_invalid_citations():
    report = evaluate_answer_citations(
        "The answer contains no source reference.",
        [{"id": "S1"}, {"id": "W1"}],
    )

    assert report["citation_count"] == 0
    assert report["citation_precision"] is None
    assert report["source_coverage"] == 0.0
    assert report["uncited_source_ids"] == ["S1", "W1"]
    assert report["unsupported_citation_ids"] == []


def test_citations_without_available_sources_are_unsupported():
    report = evaluate_answer_citations("Evidence is [S3] and [W1].", [])

    assert report["citation_count"] == 2
    assert report["valid_citation_count"] == 0
    assert report["unsupported_citation_count"] == 2
    assert report["unsupported_citation_ids"] == ["S3", "W1"]
    assert report["citation_precision"] == 0.0
    assert report["source_coverage"] is None


def test_only_app_style_ids_are_counted_as_citations():
    answer = "See [IPv6], [chapter 2], [SOURCE S1: notes.txt], and [S1: notes.txt]."
    report = evaluate_answer_citations(answer, [{"id": "S1"}])

    assert report["citation_count"] == 0
    assert report["citation_precision"] is None
    assert report["source_coverage"] == 0.0


def test_source_ids_are_deduplicated_and_malformed_metadata_is_ignored():
    report = evaluate_answer_citations(
        "The same source appears twice [S1] [S1].",
        [None, {"id": "S1"}, {"id": "S1"}, {"id": "bad id"}, {"filename": "no id"}],
    )

    assert report["citation_count"] == 2
    assert report["valid_citation_count"] == 2
    assert report["available_source_count"] == 1
    assert report["citation_precision"] == 1.0
    assert report["source_coverage"] == 1.0


@pytest.mark.parametrize("answer_text", ["", None])
def test_missing_answer_text_does_not_raise(answer_text):
    report = evaluate_answer_citations(answer_text, [{"id": "S1"}])

    assert report["citation_count"] == 0
    assert report["citation_precision"] is None
    assert report["source_coverage"] == 0.0
