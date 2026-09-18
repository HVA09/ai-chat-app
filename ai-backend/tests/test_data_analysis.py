"""اختبارات أداة تحليل بيانات CSV/XLSX."""
from pathlib import Path

from app.services.tools.data_analysis import (
    DataAnalysisError,
    DataFile,
    analyze_file,
    extract_data_analysis_request,
)


def test_extract_data_analysis_command():
    assert extract_data_analysis_request("/analyze sales.csv") == "sales.csv"
    assert extract_data_analysis_request("/data report.xlsx") == "report.xlsx"
    assert extract_data_analysis_request("حلل هذا الملف") is None


def test_analyze_csv(tmp_path: Path):
    path = tmp_path / "sales.csv"
    path.write_text(
        "name,amount,city\nAlice,10,Tripoli\nBob,20,Benghazi\nAlice,30,Tripoli\n",
        encoding="utf-8",
    )
    result = analyze_file(
        DataFile(path=path, original_filename="sales.csv", content_type="text/csv")
    )
    assert "الصفوف: **3**" in result
    assert "الأعمدة: **3**" in result
    assert "**amount**" in result
    assert "متوسط: 20" in result
    assert "Alice (2)" in result


def test_analyze_xlsx(tmp_path: Path):
    from openpyxl import Workbook

    path = tmp_path / "report.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet.append(["item", "value"])
    sheet.append(["A", 10])
    sheet.append(["B", 30])
    workbook.save(path)
    workbook.close()

    result = analyze_file(
        DataFile(
            path=path,
            original_filename="report.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    )
    assert "report.xlsx — Data" in result
    assert "متوسط: 20" in result


def test_analyze_rejects_unsupported_extension(tmp_path: Path):
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")
    try:
        analyze_file(
            DataFile(path=path, original_filename="notes.txt", content_type="text/plain")
        )
        raise AssertionError("expected DataAnalysisError")
    except DataAnalysisError as exc:
        assert "CSV وXLSX" in str(exc)
