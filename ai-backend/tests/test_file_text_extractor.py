"""اختبارات استخراج النص من الملفات."""
from pathlib import Path

from docx import Document
from openpyxl import Workbook
from pypdf import PdfWriter

from app.services import file_text_extractor
from app.services.file_text_extractor import extract_text


def test_extract_text_file(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("Hello Linux\nPython and Cloud", encoding="utf-8")

    text = extract_text(path, "text/plain")

    assert "Hello Linux" in text
    assert "Python and Cloud" in text


def test_extract_csv_file(tmp_path: Path):
    path = tmp_path / "data.csv"
    path.write_text("name,age\nMohamed,25\nSara,30\n", encoding="utf-8")

    text = extract_text(path, "text/csv")

    assert "name | age" in text
    assert "Mohamed | 25" in text


def test_extract_docx_file(tmp_path: Path):
    path = tmp_path / "doc.docx"
    document = Document()
    document.add_paragraph("Linux administration basics")
    document.save(path)

    text = extract_text(
        path,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert "Linux administration basics" in text


def test_extract_xlsx_file(tmp_path: Path):
    path = tmp_path / "sheet.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Data"
    worksheet.append(["name", "score"])
    worksheet.append(["Mohamed", 95])
    workbook.save(path)

    text = extract_text(
        path,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    assert "[ورقة: Data]" in text
    assert "Mohamed | 95" in text


def test_extract_pdf_file(tmp_path: Path):
    path = tmp_path / "empty.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with path.open("wb") as file:
        writer.write(file)

    assert extract_text(path, "application/pdf") == ""


def test_text_and_csv_extraction_respect_output_limit(tmp_path: Path):
    text_path = tmp_path / "large.txt"
    text_path.write_text("0123456789" * 100, encoding="utf-8")
    csv_path = tmp_path / "large.csv"
    csv_path.write_text("value\n" + ("abcdefghij\n" * 100), encoding="utf-8")

    text = extract_text(text_path, "text/plain", max_chars=12)
    csv = extract_text(csv_path, "text/csv", max_chars=12)

    assert text.startswith("0123456789")
    assert text.endswith("[تم اختصار المحتوى بسبب الحد المسموح]")
    assert csv.startswith("value")
    assert csv.endswith("[تم اختصار المحتوى بسبب الحد المسموح]")



def test_text_and_csv_read_only_bounded_source_prefixes(tmp_path: Path, monkeypatch):
    text_path = tmp_path / "bounded.txt"
    text_path.write_text("x" * 1000, encoding="utf-8")
    csv_path = tmp_path / "bounded.csv"
    csv_path.write_text("x\n" * 1000, encoding="utf-8")

    real_open = Path.open
    read_sizes = []

    class ReadSpy:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.stream.close()

        def read(self, size=-1):
            read_sizes.append(size)
            return self.stream.read(size)

    def tracked_open(path, *args, **kwargs):
        return ReadSpy(real_open(path, *args, **kwargs))

    monkeypatch.setattr(Path, "open", tracked_open)

    extract_text(text_path, "text/plain", max_chars=16)
    extract_text(csv_path, "text/csv", max_chars=16)

    assert read_sizes == [64, 128]



def test_xlsx_extraction_bounds_sheet_dimensions_and_total_cells(tmp_path: Path, monkeypatch):
    calls = []

    class Worksheet:
        title = "Large"

        def iter_rows(self, **kwargs):
            calls.append(kwargs)
            yield ("Linux", "Cloud")

    class WorkbookStub:
        worksheets = [Worksheet()]

        def close(self):
            pass

    monkeypatch.setattr(file_text_extractor, "load_workbook", lambda **_kwargs: WorkbookStub())

    text = extract_text(
        tmp_path / "stub.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    assert "[ورقة: Large]" in text
    assert "Linux | Cloud" in text
    assert calls == [{
        "max_row": file_text_extractor.MAX_XLSX_ROWS_PER_SHEET,
        "max_col": file_text_extractor.MAX_XLSX_COLUMNS_PER_ROW,
        "values_only": True,
    }]



def test_pdf_extraction_stops_at_page_limit(tmp_path: Path, monkeypatch):
    extracted = []

    class Page:
        def __init__(self, number):
            self.number = number

        def extract_text(self):
            extracted.append(self.number)
            return f"page {self.number}"

    class Reader:
        pages = [Page(number) for number in range(file_text_extractor.MAX_PDF_PAGES + 5)]

    monkeypatch.setattr(file_text_extractor, "PdfReader", lambda _path: Reader())

    text = extract_text(tmp_path / "stub.pdf", "application/pdf")

    assert len(extracted) == file_text_extractor.MAX_PDF_PAGES
    assert "page 99" in text
    assert "page 100" not in text
