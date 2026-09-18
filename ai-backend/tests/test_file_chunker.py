"""اختبارات تقسيم النص."""
import pytest

from app.services.file_chunker import chunk_text


def test_chunk_text_splits_large_text_with_overlap():
    text = "A" * 5000

    chunks = chunk_text(text, chunk_size=1000, overlap=200)

    assert len(chunks) == 7
    assert chunks[0][-200:] == chunks[1][:200]


def test_chunk_text_empty_returns_empty():
    assert chunk_text("   ") == []


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=10, overlap=10)
