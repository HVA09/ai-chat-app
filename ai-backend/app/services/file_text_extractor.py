"""استخراج نص آمن ومحدود من الملفات القابلة للقراءة قبل إدخالها إلى سياق AI."""
from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

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

# Spreadsheet traversal limits are independent of rendered output size.
MAX_XLSX_SHEETS = 20
MAX_XLSX_ROWS_PER_SHEET = 1_000
MAX_XLSX_COLUMNS_PER_ROW = 50
MAX_XLSX_CELLS_TOTAL = 50_000
MAX_PDF_PAGES = 100
MAX_DOCX_PARAGRAPHS = 2_000
MAX_DOCX_TABLE_ROWS = 1_000

# OOXML files are ZIP containers; bound both the central directory and expansion.
MAX_OOXML_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_OOXML_ARCHIVE_ENTRIES = 4_096
MAX_OOXML_TOTAL_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_OOXML_MEMBER_UNCOMPRESSED_BYTES = 32 * 1024 * 1024
MAX_OOXML_COMPRESSION_RATIO = 200


class FileTextExtractionError(Exception):
    """فشل في قراءة محتوى الملف."""


def _limit(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[تم اختصار المحتوى بسبب الحد المسموح]"


def _read_text_file(path: Path, max_chars: int) -> str:
    # Read only a bounded prefix; Path.read_bytes() would load the entire upload.
    with path.open("rb") as source:
        raw = source.read(max_chars * 4)
    text = raw.decode("utf-8-sig", errors="replace")
    return _limit(text, max_chars)


def _read_csv_file(path: Path, max_chars: int) -> str:
    # Keep the CSV input buffer bounded before handing it to csv.reader.
    with path.open("rb") as source:
        raw = source.read(max_chars * 8)
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
    for page_number, page in enumerate(reader.pages):
        if page_number >= MAX_PDF_PAGES:
            parts.append("[تم اختصار ملف PDF بسبب حد عدد الصفحات]")
            break
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue
        parts.append(page_text)
        used += len(page_text) + 1
        if used >= max_chars:
            break
    return _limit("\n\n".join(parts), max_chars)



def _validate_ooxml_archive(path: Path) -> None:
    """Reject oversized OOXML ZIP containers before document libraries parse them."""
    try:
        archive_size = path.stat().st_size
        if archive_size > MAX_OOXML_ARCHIVE_BYTES:
            raise FileTextExtractionError("document archive exceeds size limit")

        with ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > MAX_OOXML_ARCHIVE_ENTRIES:
                raise FileTextExtractionError("document archive has too many entries")

            total_uncompressed = 0
            for member in members:
                if member.file_size > MAX_OOXML_MEMBER_UNCOMPRESSED_BYTES:
                    raise FileTextExtractionError("document archive member exceeds size limit")
                total_uncompressed += member.file_size
                if total_uncompressed > MAX_OOXML_TOTAL_UNCOMPRESSED_BYTES:
                    raise FileTextExtractionError("document archive expansion exceeds size limit")
                if member.file_size and (
                    member.compress_size == 0
                    or member.file_size / member.compress_size > MAX_OOXML_COMPRESSION_RATIO
                ):
                    raise FileTextExtractionError("document archive compression ratio exceeds limit")
    except BadZipFile as exc:
        raise FileTextExtractionError("document archive is invalid") from exc


def _read_docx_file(path: Path, max_chars: int) -> str:
    _validate_ooxml_archive(path)
    document = Document(str(path))
    parts: list[str] = []
    used = 0
    rows_scanned = 0
    truncated = len(document.paragraphs) > MAX_DOCX_PARAGRAPHS

    for paragraph in document.paragraphs[:MAX_DOCX_PARAGRAPHS]:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
            used += len(text) + 1
        if used >= max_chars:
            return _limit("\n".join(parts), max_chars)

    for table in document.tables:
        for row in table.rows:
            if rows_scanned >= MAX_DOCX_TABLE_ROWS:
                truncated = True
                break
            rows_scanned += 1
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            if any(cells):
                line = " | ".join(cells)
                parts.append(line)
                used += len(line) + 1
            if used >= max_chars:
                return _limit("\n".join(parts), max_chars)
        if rows_scanned >= MAX_DOCX_TABLE_ROWS:
            break

    if truncated:
        parts.append("[تم اختصار مستند Word بسبب حدود المعالجة]")
    return _limit("\n".join(parts), max_chars)


def _read_xlsx_file(path: Path, max_chars: int) -> str:
    _validate_ooxml_archive(path)
    workbook = load_workbook(filename=str(path), read_only=True, data_only=True)
    parts: list[str] = []
    used = 0
    cells_scanned = 0
    truncated = len(workbook.worksheets) > MAX_XLSX_SHEETS
    try:
        for worksheet in workbook.worksheets[:MAX_XLSX_SHEETS]:
            parts.append(f"[ورقة: {worksheet.title}]")
            used += len(parts[-1]) + 1
            for row in worksheet.iter_rows(
                max_row=MAX_XLSX_ROWS_PER_SHEET,
                max_col=MAX_XLSX_COLUMNS_PER_ROW,
                values_only=True,
            ):
                cells_scanned += len(row)
                values = [
                    str(value).strip()
                    for value in row
                    if value is not None and str(value).strip()
                ]
                if values:
                    line = " | ".join(values)
                    parts.append(line)
                    used += len(line) + 1
                if used >= max_chars:
                    return _limit("\n".join(parts), max_chars)
                if cells_scanned >= MAX_XLSX_CELLS_TOTAL:
                    truncated = True
                    break
            if cells_scanned >= MAX_XLSX_CELLS_TOTAL:
                break
        if truncated:
            parts.append("[تم اختصار جداول البيانات بسبب حدود المعالجة]")
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
