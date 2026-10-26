"""اختبارات استخراج النص من الملفات."""
from pathlib import Path

from docx import Document
from openpyxl import Workbook
from pypdf import PdfWriter

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


def test_docx_extraction_stops_building_text_after_character_limit(
    tmp_path: Path, monkeypatch
):
    from app.services import file_text_extractor

    class FakeParagraph:
        def __init__(self, text: str):
            self.text = text

    class TrackingParagraphs:
        def __init__(self):
            self.visited = 0

        def __iter__(self):
            self.visited += 1
            yield FakeParagraph("A" * 1000)
            self.visited += 1
            yield FakeParagraph("This later paragraph should not be visited.")

    paragraphs = TrackingParagraphs()

    class FakeDocument:
        def __init__(self):
            self.paragraphs = paragraphs
            self.tables = []

    monkeypatch.setattr(file_text_extractor, "Document", lambda _path: FakeDocument())

    text = file_text_extractor._read_docx_file(tmp_path / "fake.docx", max_chars=20)

    assert text.startswith("A" * 20)
    assert "[تم اختصار المحتوى بسبب الحد المسموح]" in text
    assert paragraphs.visited == 1
    assert "later paragraph" not in text
