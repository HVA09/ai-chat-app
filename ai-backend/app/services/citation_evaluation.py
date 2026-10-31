"""Offline checks for citation IDs in generated answers."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


_SOURCE_ID_PATTERN = re.compile(r"[SWD]\d+\Z")
_CITATION_PATTERN = re.compile(r"\[(?P<source_id>[SWD]\d+)\]")
_FENCE_OPEN_PATTERN = re.compile(r"^[ \t]{0,3}(?P<marker>`{3,}|~{3,})(?P<info>[^\r\n]*)$")
_FENCE_CLOSE_PATTERN = re.compile(r"^[ \t]{0,3}(?P<marker>`+|~+)[ \t]*$")
_INLINE_CODE_PATTERN = re.compile(r"(?<!`)(?P<ticks>`+)(?P<code>.*?)(?P=ticks)(?!`)", re.DOTALL)


def _strip_fenced_code_blocks(text: str) -> str:
    """Remove fenced Markdown code blocks while preserving paragraph boundaries."""
    rendered: list[str] = []
    fence_character: str | None = None
    fence_length = 0

    for line in text.splitlines(keepends=True):
        line_content = line.rstrip("\r\n")
        newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""

        if fence_character is not None:
            closing = _FENCE_CLOSE_PATTERN.match(line_content)
            if (
                closing
                and closing.group("marker")[0] == fence_character
                and len(closing.group("marker")) >= fence_length
            ):
                fence_character = None
                fence_length = 0
            rendered.append(newline)
            continue

        opening = _FENCE_OPEN_PATTERN.match(line_content)
        if opening:
            marker = opening.group("marker")
            info = opening.group("info")
            # Markdown forbids backticks in a backtick-fence info string.
            if marker[0] == "`" and "`" in info:
                rendered.append(line)
                continue
            fence_character = marker[0]
            fence_length = len(marker)
            rendered.append(newline)
            continue

        rendered.append(line)

    return "".join(rendered)


def _citation_search_text(answer_text: str) -> str:
    """Ignore citations inside fenced and inline Markdown code examples."""
    without_fences = _strip_fenced_code_blocks(answer_text)
    return _INLINE_CODE_PATTERN.sub(lambda match: " " * len(match.group()), without_fences)


def evaluate_answer_citations(
    answer_text: str,
    sources: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Check citation-ID consistency without judging semantic support.

    Only app-style IDs such as [S1], [W2], and [D3] in answer prose are counted.
    App-style markers inside fenced or inline Markdown code are ignored. This checks
    ID consistency only; it does not prove semantic source support.
    The function is deterministic and performs no network, model, or database calls.
    """
    rendered_answer = answer_text if isinstance(answer_text, str) else ""
    references = _CITATION_PATTERN.findall(_citation_search_text(rendered_answer))

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
