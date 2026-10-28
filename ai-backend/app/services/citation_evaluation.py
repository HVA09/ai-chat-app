"""Offline checks for citation IDs in generated answers."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


_SOURCE_ID_PATTERN = re.compile(r"[SWD]\d+\Z")
_CITATION_PATTERN = re.compile(r"\[(?P<source_id>[SWD]\d+)\]")


def evaluate_answer_citations(
    answer_text: str,
    sources: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Check citation-ID consistency without judging semantic support.

    Only app-style IDs such as [S1], [W2], and [D3] are counted.
    The function is deterministic and performs no network, model, or database calls.
    """
    rendered_answer = answer_text if isinstance(answer_text, str) else ""
    references = _CITATION_PATTERN.findall(rendered_answer)

    available_ids: set[str] = set()
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        source_id = source.get("id")
        if isinstance(source_id, str) and _SOURCE_ID_PATTERN.fullmatch(source_id):
            available_ids.add(source_id)

    valid_count = sum(source_id in available_ids for source_id in references)
    cited_available_ids = set(references) & available_ids
    unsupported_ids = sorted(set(references) - available_ids)
    citation_precision = (
        round(valid_count / len(references), 4) if references else None
    )
    source_coverage = (
        round(len(cited_available_ids) / len(available_ids), 4)
        if available_ids
        else None
    )

    return {
        "citation_count": len(references),
        "valid_citation_count": valid_count,
        "unsupported_citation_count": len(references) - valid_count,
        "unsupported_citation_ids": unsupported_ids,
        "available_source_count": len(available_ids),
        "cited_source_ids": sorted(cited_available_ids),
        "uncited_source_ids": sorted(available_ids - cited_available_ids),
        "citation_precision": citation_precision,
        "source_coverage": source_coverage,
    }
