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
