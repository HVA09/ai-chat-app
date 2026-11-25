"""Tests for the spawned parser supervisor primitive."""
from pathlib import Path

import pytest

from app.services.file_extraction_supervisor import (
    ExtractionSupervisorError,
    extract_text_isolated,
)
from app.services.file_text_extractor import FileTextExtractionError


def test_isolated_extractor_returns_bounded_text(tmp_path: Path):
    source = tmp_path / "source.txt"
    source.write_text("Linux, networking, and cloud", encoding="utf-8")

    result = extract_text_isolated(
        source,
        "text/plain",
        max_chars=128,
        timeout_seconds=5,
        heartbeat_interval_seconds=1,
    )

    assert result == "Linux, networking, and cloud"


def test_isolated_extractor_returns_none_for_unsupported_content_type(
    tmp_path: Path,
):
    source = tmp_path / "image.bin"
    source.write_bytes(b"not text")

    result = extract_text_isolated(
        source,
        "application/octet-stream",
        timeout_seconds=5,
        heartbeat_interval_seconds=1,
    )

    assert result is None


def test_isolated_extractor_rejects_invalid_timing_before_spawn(
    tmp_path: Path,
):
    source = tmp_path / "source.txt"
    source.write_text("safe", encoding="utf-8")

    with pytest.raises(ExtractionSupervisorError, match="invalid_supervisor_timing"):
        extract_text_isolated(
            source,
            "text/plain",
            timeout_seconds=1,
            heartbeat_interval_seconds=1,
        )


def test_isolated_extractor_reports_parser_failure_without_details(
    tmp_path: Path,
):
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"not a valid PDF")

    with pytest.raises(FileTextExtractionError):
        extract_text_isolated(
            source,
            "application/pdf",
            timeout_seconds=5,
            heartbeat_interval_seconds=1,
        )
