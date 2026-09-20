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


class FileTextExtractionError(Exception):
    """فشل في قراءة محتوى الملف."""


def _limit(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[تم اختصار المحتوى بسبب الحد المسموح]"


def _read_text_file(path: Path, max_chars: int) -> str:
    raw = path.read_bytes()[: max_chars * 4]
    text = raw.decode("utf-8-sig", errors="replace")
    return _limit(text, max_chars)


def _read_csv_file(path: Path, max_chars: int) -> str:
    raw = path.read_bytes()[: max_chars * 8]
    text = raw.decode("utf-8-sig", errors="replace")
    rows = csv.reader(StringIO(text))
    rendered = []
    used = 0
    for row in rows:
        line = " | ".join(cell.strip() for cell in row)
        if not line:
            continue
        rendered.append(line)
        used += len(line) + 1
        if used >= max_chars:
            break
    return _limit("\n".join(rendered), max_chars)


def _read_pdf_file(path: Path, max_chars: int) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    used = 0
    for page in reader.pages:
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue
        parts.append(page_text)
        used += len(page_text) + 1
        if used >= max_chars:
            break
    return _limit("\n\n".join(parts), max_chars)


def _read_docx_file(path: Path, max_chars: int) -> str:
    document = Document(str(path))
    parts: list[str] = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))

    return _limit("\n".join(parts), max_chars)


def _read_xlsx_file(path: Path, max_chars: int) -> str:
    workbook = load_workbook(filename=str(path), read_only=True, data_only=True)
    parts: list[str] = []
    used = 0
    try:
        for worksheet in workbook.worksheets:
            parts.append(f"[ورقة: {worksheet.title}]")
            used += len(parts[-1]) + 1
            for row in worksheet.iter_rows(values_only=True):
                values = [
                    str(value).strip()
                    for value in row
                    if value is not None and str(value).strip()
                ]
                if not values:
                    continue
                line = " | ".join(values)
                parts.append(line)
                used += len(line) + 1
                if used >= max_chars:
                    return _limit("\n".join(parts), max_chars)
        return _limit("\n".join(parts), max_chars)
    finally:
        workbook.close()


def extract_text(
    path: str | Path,
    content_type: str,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str | None:
    """يرجع النص المستخرج، أو None للملفات غير النصية (مثل الصور)."""
    if content_type not in SUPPORTED_TEXT_TYPES:
        return None

    path = Path(path)
    try:
        if content_type == "text/plain":
            return _read_text_file(path, max_chars)
        if content_type in {"text/csv", "application/vnd.ms-excel"}:
            return _read_csv_file(path, max_chars)
        if content_type == "application/pdf":
            return _read_pdf_file(path, max_chars)
        if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return _read_docx_file(path, max_chars)
        if content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            return _read_xlsx_file(path, max_chars)
    except Exception as exc:
        raise FileTextExtractionError(str(exc)) from exc

    return None
