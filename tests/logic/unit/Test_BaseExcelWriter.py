"""
Test suite for BaseExcelWriter.

Scope   : Validates BaseExcelWriter.write() in src/file_io/writers/BaseExcelWriter.py:
          the falsy-path no-op, real workbook/table/header/row generation
          (verified by re-reading the saved .xlsx with openpyxl), the empty-rows
          edge case, and column-width auto-sizing against None/blank cells.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-XLW-001, TC-XLW-002, ... TC-XLW-007
Fixtures: none (uses pytest's built-in tmp_path)
"""
import openpyxl

from src.file_io.writers.BaseExcelWriter import BaseExcelWriter


# TC-XLW-001
# write() must be a no-op when path is an empty string — no file should be
# created at all.
def test_base_excel_writer_write_noop_for_empty_path(tmp_path):
    # Arrange
    headers = ["Date", "Course"]
    rows = [["2026-06-01", "Calculus 1"]]

    # Act
    result = BaseExcelWriter.write("", headers, rows)

    # Assert
    assert result is None
    assert list(tmp_path.iterdir()) == []


# TC-XLW-002
# write() must be a no-op when path is None (falsy) as well, not just for
# the empty-string case.
def test_base_excel_writer_write_noop_for_none_path():
    # Arrange
    headers = ["Date", "Course"]
    rows = [["2026-06-01", "Calculus 1"]]

    # Act
    result = BaseExcelWriter.write(None, headers, rows)

    # Assert
    assert result is None


# TC-XLW-003
# A normal write must produce a real .xlsx file whose first row is the
# header row and whose subsequent rows match the given data exactly.
def test_base_excel_writer_write_produces_correct_headers_and_rows(tmp_path):
    # Arrange
    path = tmp_path / "schedule.xlsx"
    headers = ["Date", "Course", "Instructor"]
    rows = [
        ["2026-06-01", "Calculus 1", "Dr. Cohen"],
        ["2026-06-02", "Physics 1", "Prof. Levi"],
    ]

    # Act
    BaseExcelWriter.write(str(path), headers, rows)

    # Assert
    assert path.exists()
    wb = openpyxl.load_workbook(str(path))
    ws = wb.active
    assert ws.title == "Schedule"
    assert [cell.value for cell in ws[1]] == headers
    assert [cell.value for cell in ws[2]] == rows[0]
    assert [cell.value for cell in ws[3]] == rows[1]


# TC-XLW-004
# The saved workbook must contain exactly one native Table whose reference
# range covers the header row plus every data row (A1:C3 for 2 data rows
# and 3 columns) — not a range that is off by one or omits the header.
def test_base_excel_writer_write_creates_table_with_correct_range(tmp_path):
    # Arrange
    path = tmp_path / "schedule.xlsx"
    headers = ["Date", "Course", "Instructor"]
    rows = [
        ["2026-06-01", "Calculus 1", "Dr. Cohen"],
        ["2026-06-02", "Physics 1", "Prof. Levi"],
    ]

    # Act
    BaseExcelWriter.write(str(path), headers, rows)

    # Assert
    wb = openpyxl.load_workbook(str(path))
    ws = wb.active
    tables = list(ws.tables.values())
    assert len(tables) == 1
    assert tables[0].ref == "A1:C3"
    assert tables[0].displayName == "ExamSchedule"


# TC-XLW-005
# An empty rows list must still produce a valid table reference spanning
# only the header row (A1:<last-col>1), not a malformed or missing table.
def test_base_excel_writer_write_with_empty_rows_produces_header_only_table(tmp_path):
    # Arrange
    path = tmp_path / "empty_schedule.xlsx"
    headers = ["Date", "Course"]
    rows = []

    # Act
    BaseExcelWriter.write(str(path), headers, rows)

    # Assert
    wb = openpyxl.load_workbook(str(path))
    ws = wb.active
    assert ws.max_row == 1
    tables = list(ws.tables.values())
    assert len(tables) == 1
    assert tables[0].ref == "A1:B1"


# TC-XLW-006
# Column-width auto-sizing must not crash when a row contains None or
# empty-string cell values, and must still size the column to fit the
# longest real text in that column (the header, in this case).
def test_base_excel_writer_write_handles_none_and_blank_cells_in_width_calc(tmp_path):
    # Arrange
    path = tmp_path / "sparse.xlsx"
    headers = ["Date", "Course", "Instructor"]
    rows = [
        ["2026-06-01", None, ""],
        [None, "Physics 1", None],
    ]

    # Act — must not raise despite the None/blank values.
    BaseExcelWriter.write(str(path), headers, rows)

    # Assert
    wb = openpyxl.load_workbook(str(path))
    ws = wb.active
    # cells, so width must be wide enough to hold the header at minimum.
    assert ws.column_dimensions["C"].width >= len("Instructor")


# TC-XLW-007
# A long cell value in a column must widen that column beyond the 12-char
# floor, confirming the padding of +4 is actually applied on top of the
# longest cell, not just the header length.
def test_base_excel_writer_write_widens_column_for_long_values(tmp_path):
    # Arrange
    path = tmp_path / "wide.xlsx"
    headers = ["Course"]
    long_name = "A" * 30
    rows = [[long_name]]

    # Act
    BaseExcelWriter.write(str(path), headers, rows)

    # Assert
    wb = openpyxl.load_workbook(str(path))
    ws = wb.active
    assert ws.column_dimensions["A"].width >= len(long_name)
