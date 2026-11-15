"""استخراج نص آمن ومحدود من الملفات القابلة للقراءة قبل إدخالها إلى سياق AI."""
from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader


SUPPORTED_TEXT_TYPES = {
    "text/plain",
    "text/csv",
    "application/vnd.ms-excel",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

DEFAULT_MAX_CHARS = 20_000
DEFAULT_MAX_PDF_PAGES = 200
TRUNCATION_MARKER = "[تم اختصار المحتوى بسبب الحد المسموح]"


class FileTextExtractionError(Exception):
    """فشل في قراءة محتوى الملف."""


def _with_truncation_marker(
    text: str,
    max_chars: int,
    marker: str = TRUNCATION_MARKER,
) -> str:
    return f"{text[:max_chars].rstrip()}\n\n{marker}"


def _limit(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return _with_truncation_marker(text, max_chars)


def _read_bounded_bytes(path: Path, max_bytes: int) -> tuple[bytes, bool]:
    """Read no more than max_bytes plus one sentinel byte to detect truncation."""
    with path.open("rb") as source:
        raw = source.read(max_bytes + 1)
    return raw[:max_bytes], len(raw) > max_bytes


def _append_bounded_part(
    parts: list[str],
    value: str,
    used: int,
    max_chars: int,
    separator: str = "\n",
) -> tuple[int, bool]:
    """Append one fragment, accounting for the exact separator used when joining."""
    if not value:
        return used, False
    separator_size = len(separator) if parts else 0
    remaining = max_chars - used - separator_size
    if remaining <= 0:
        return used, True
    if len(value) > remaining:
        parts.append(value[:remaining])
        return max_chars, True
    parts.append(value)
    used += separator_size + len(value)
    return used, used >= max_chars


def _read_text_file(path: Path, max_chars: int) -> str:
    raw, truncated = _read_bounded_bytes(path, max_chars * 4)
    text = raw.decode("utf-8-sig", errors="replace")
    if truncated:
        return _with_truncation_marker(text, max_chars)
    return _limit(text, max_chars)


def _read_csv_file(path: Path, max_chars: int) -> str:
    raw, byte_truncated = _read_bounded_bytes(path, max_chars * 8)
    text = raw.decode("utf-8-sig", errors="replace")
    rows = csv.reader(StringIO(text))
    rendered: list[str] = []
    used = 0
    row_truncated = False
    for row in rows:
        line = " | ".join(cell.strip() for cell in row)
        if not line:
            continue
        used, row_truncated = _append_bounded_part(rendered, line, used, max_chars)
        if row_truncated:
            break
    result = "\n".join(rendered)
    if byte_truncated or row_truncated:
        return _with_truncation_marker(result, max_chars)
    return _limit(result, max_chars)


def _read_pdf_file(
    path: Path,
    max_chars: int,
    max_pages: int = DEFAULT_MAX_PDF_PAGES,
) -> str:
    reader = PdfReader(str(path))
    pages = reader.pages
    page_limit_hit = len(pages) > max_pages
    parts: list[str] = []
    used = 0
    for page in pages[:max_pages]:
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue
        used, char_limit_hit = _append_bounded_part(
            parts, page_text, used, max_chars, separator="\\n\\n"
        )
        if char_limit_hit:
            break
    result = "\n\n".join(parts)
    if page_limit_hit and used < max_chars:
        return _with_truncation_marker(
            result,
            max_chars,
            "[تم اختصار الملف بسبب الحد الأقصى لعدد صفحات PDF]",
        )
    return _limit(result, max_chars)


def _read_docx_file(path: Path, max_chars: int) -> str:
    document = Document(str(path))
    parts: list[str] = []
    used = 0
    truncated = False

    for paragraph in document.paragraphs:
        used, truncated = _append_bounded_part(
            parts, paragraph.text.strip(), used, max_chars
        )
        if truncated:
            break

    if not truncated:
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                if any(cells):
                    used, truncated = _append_bounded_part(
                        parts, " | ".join(cells), used, max_chars
                    )
                    if truncated:
                        break
            if truncated:
                break

    result = "\n".join(parts)
    if truncated:
        return _with_truncation_marker(result, max_chars)
    return _limit(result, max_chars)


def _read_xlsx_file(path: Path, max_chars: int) -> str:
    workbook = load_workbook(filename=str(path), read_only=True, data_only=True)
    parts: list[str] = []
    used = 0
    truncated = False
    try:
        for worksheet in workbook.worksheets:
            used, truncated = _append_bounded_part(
                parts, f"[ورقة: {worksheet.title}]", used, max_chars
            )
            if truncated:
                break
            for row in worksheet.iter_rows(values_only=True):
                values = [
                    str(value).strip()
                    for value in row
                    if value is not None and str(value).strip()
                ]
                if not values:
                    continue
                used, truncated = _append_bounded_part(
                    parts, " | ".join(values), used, max_chars
                )
                if truncated:
                    break
            if truncated:
                break
        result = "\n".join(parts)
        if truncated:
            return _with_truncation_marker(result, max_chars)
        return _limit(result, max_chars)
    finally:
        workbook.close()


def extract_text(
    path: str | Path,
    content_type: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    max_pdf_pages: int = DEFAULT_MAX_PDF_PAGES,
) -> str | None:
    """يرجع النص المستخرج، أو None للملفات غير النصية (مثل الصور)."""
    if content_type not in SUPPORTED_TEXT_TYPES:
        return None
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if max_pdf_pages <= 0:
        raise ValueError("max_pdf_pages must be positive")

    path = Path(path)
    try:
        if content_type == "text/plain":
            return _read_text_file(path, max_chars)
        if content_type in {"text/csv", "application/vnd.ms-excel"}:
            return _read_csv_file(path, max_chars)
        if content_type == "application/pdf":
            return _read_pdf_file(path, max_chars, max_pdf_pages)
        if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return _read_docx_file(path, max_chars)
        if content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            return _read_xlsx_file(path, max_chars)
    except Exception as exc:
        raise FileTextExtractionError(str(exc)) from exc

    return None
