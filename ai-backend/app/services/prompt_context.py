"""Sanitize known app-level prompt delimiters in untrusted content."""
from __future__ import annotations

import re


_CONTEXT_CONTROL_MARKER_PATTERN = re.compile(
    r"\[(?:"
    r"\s*SOURCE\s+S\d+\s*:[^\]\r\n]*"
    r"|\s*[SWD]\d+\s*"
    r"|\s*(?:USER MEMORY|PROJECT MEMORY|ASSISTANT INSTRUCTIONS|PROJECT INSTRUCTIONS|CONVERSATION SUMMARY|BEGIN UNTRUSTED TOOL DATA)\s*"
    r"|\s*END\s+(?:RETRIEVED FILE CONTEXT|FILE CONTEXT|EXPLICIT ATTACHMENT CONTEXT|"
    r"ATTACHMENT STATUS|USER MEMORY|PROJECT MEMORY|ASSISTANT INSTRUCTIONS|"
    r"PROJECT INSTRUCTIONS|CONVERSATION SUMMARY|UNTRUSTED TOOL DATA)\s*"
    r"|\s*ATTACHMENT STATUS\s+—\s+VERIFIED APPLICATION METADATA\s*"
    r")\]",
    re.IGNORECASE,
)


_USER_REQUEST_DELIMITER_PATTERN = re.compile(
    r"(?i)\bUSER\s+REQUEST\s*:"
)


def safe_context_text(text: str) -> str:
    """Neutralize known app-level context markers in prompt-bound content.

    This changes only the rendered copy passed to the model; stored text and source
    metadata remain unchanged. It reduces delimiter and citation spoofing, but does
    not stop every prompt injection or replace source/permission validation.
    """
    rendered = _CONTEXT_CONTROL_MARKER_PATTERN.sub(
        lambda match: f"［{match.group(0)[1:-1]}］",
        text,
    )
    # The final user request is separated by this literal delimiter in the prompt.
    # Prevent file, memory, and metadata text from imitating that delimiter.
    return _USER_REQUEST_DELIMITER_PATTERN.sub("USER REQUEST∶", rendered)
