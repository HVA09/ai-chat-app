"""Sanitize known app-level prompt delimiters in untrusted content."""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable


_CONTEXT_CONTROL_MARKER_PATTERN = re.compile(
    r"\[(?:"
    r"\s*SOURCE\s+S\d+\s*:[^\]\r\n]*"
    r"|\s*[SWD]\d+\s*"
    r"|\s*(?:USER MEMORY|PROJECT MEMORY|ASSISTANT INSTRUCTIONS|PROJECT INSTRUCTIONS|CONVERSATION SUMMARY|BEGIN UNTRUSTED TOOL DATA|BEGIN UNTRUSTED TRANSCRIPT(?: JSON)?)\s*"
    r"|\s*END\s+(?:RETRIEVED FILE CONTEXT|FILE CONTEXT|EXPLICIT ATTACHMENT CONTEXT|"
    r"ATTACHMENT STATUS|USER MEMORY|PROJECT MEMORY|ASSISTANT INSTRUCTIONS|"
    r"PROJECT INSTRUCTIONS|CONVERSATION SUMMARY|UNTRUSTED TOOL DATA|UNTRUSTED TRANSCRIPT(?: JSON)?)\s*"
    r"|\s*ATTACHMENT STATUS\s+—\s+VERIFIED APPLICATION METADATA\s*"
    r")\]",
    re.IGNORECASE,
)


_MARKER_FORMAT_CHARS = r"\u00ad\u200b\u200c\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069"
_OPTIONAL_MARKER_FORMAT = rf"[{_MARKER_FORMAT_CHARS}]*"
_MARKER_SEPARATOR = rf"[\s{_MARKER_FORMAT_CHARS}]+"

_USER_REQUEST_DELIMITER_PATTERN = re.compile(
    rf"(?i)\bU{_OPTIONAL_MARKER_FORMAT}S{_OPTIONAL_MARKER_FORMAT}"
    rf"E{_OPTIONAL_MARKER_FORMAT}R{_MARKER_SEPARATOR}"
    rf"R{_OPTIONAL_MARKER_FORMAT}E{_OPTIONAL_MARKER_FORMAT}"
    rf"Q{_OPTIONAL_MARKER_FORMAT}U{_OPTIONAL_MARKER_FORMAT}"
    rf"E{_OPTIONAL_MARKER_FORMAT}S{_OPTIONAL_MARKER_FORMAT}"
    rf"T[\s{_MARKER_FORMAT_CHARS}]*[:：﹕︓∶]"
)


_UNTRUSTED_TRANSCRIPT_MARKER_PATTERN = re.compile(
    r"(?i)\b(?:BEGIN|END)\s+UNTRUSTED\s+TRANSCRIPT(?:\s+JSON)?\b"
)


def _replace_obfuscated_matches(
    text: str,
    pattern: re.Pattern[str],
    replacement: Callable[[re.Match[str]], str],
) -> str:
    """Match obfuscated markers using a normalized copy, replacing only matched spans.

    Format controls and combining marks outside app-owned marker spans are preserved.
    Compatibility normalization applies only to the matching copy, and offsets map
    each normalized character back to the original so surrounding user/file text is
    not globally rewritten.
    """
    normalized_chars: list[str] = []
    original_offsets: list[int] = []
    for index, character in enumerate(text):
        category = unicodedata.category(character)
        if character == "\u0640" or category in {"Cf", "Mn", "Me"}:
            continue
        normalized_character = unicodedata.normalize("NFKC", character)
        for normalized_unit in normalized_character:
            normalized_chars.append(normalized_unit)
            original_offsets.append(index)

    normalized_text = "".join(normalized_chars)
    matches = list(pattern.finditer(normalized_text))
    for match in reversed(matches):
        if match.start() == match.end():
            continue
        original_start = original_offsets[match.start()]
        original_end = original_offsets[match.end() - 1] + 1
        text = (
            text[:original_start]
            + replacement(match)
            + text[original_end:]
        )
    return text


def safe_context_text(text: str) -> str:
    """Neutralize known app-level context markers in prompt-bound content.

    This changes only the rendered copy passed to the model; stored text and source
    metadata remain unchanged. It reduces delimiter and citation spoofing, but does
    not stop every prompt injection or replace source/permission validation.
    """
    rendered = _replace_obfuscated_matches(
        text,
        _CONTEXT_CONTROL_MARKER_PATTERN,
        lambda match: f"［{match.group(0)[1:-1]}］",
    )
    # Transcript wrappers are also app-owned delimiters. Neutralize bare mentions
    # so a saved message cannot impersonate the beginning/end of a memory transcript.
    rendered = _replace_obfuscated_matches(
        rendered,
        _UNTRUSTED_TRANSCRIPT_MARKER_PATTERN,
        lambda match: match.group(0).replace(" ", "∶", 1),
    )
    # The final user request is separated by this literal delimiter in the prompt.
    # Prevent file, memory, and metadata text from imitating that delimiter.
    return _replace_obfuscated_matches(
        rendered,
        _USER_REQUEST_DELIMITER_PATTERN,
        lambda _match: "USER REQUEST∶",
    )
