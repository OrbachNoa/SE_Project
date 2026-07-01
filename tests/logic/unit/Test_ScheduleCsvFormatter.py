"""
Test suite for ScheduleCsvFormatter.

Scope   : Validates format_schedule_csv() in
          src/file_io/formatters/ScheduleCsvFormatter.py — the falsy-input
          short circuit, date sorting, instructor fallback, HTML/subtitle
          cleanup, tooltip-derived metadata, evaluation-type suffix, and the
          Programs column fallback placeholder.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CSV-001, TC-CSV-002, ... TC-CSV-010
Fixtures: none (uses types.SimpleNamespace duck-typed fakes, no Qt needed)
"""
import types

from src.file_io.formatters.ScheduleCsvFormatter import format_schedule_csv

EXPECTED_HEADERS = ["Date", "Course", "Instructor", "Details", "Programs"]


def _make_item(
    date="2026-06-01",
    title="Calculus 1",
    instructor="Dr. Cohen",
    subtitle="ID: 10101<br>Prog 83101 (Obligatory)",
    tooltip="Calculus 1 (10101)\n2026-06-01 · FALL · Moed ALEPH\nInstructor: Dr. Cohen · EXAM\nProg 83101 (Obligatory)",
    evaluation="EXAM",
):
    """Build a minimal duck-typed schedule item matching ScheduleItemViewModel's
    public fields, without depending on Qt or the real dataclass."""
    return types.SimpleNamespace(
        date=date,
        title=title,
        instructor=instructor,
        subtitle=subtitle,
        tooltip=tooltip,
        evaluation=evaluation,
    )


# TC-CSV-001
# A None schedule_view must return the fixed headers and an empty rows list.
def test_format_schedule_csv_returns_empty_rows_for_none_input():
    # Arrange
    schedule_view = None

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert
    assert headers == EXPECTED_HEADERS
    assert rows == []


# TC-CSV-002
# An object lacking an 'items' attribute entirely must also short-circuit
# to empty rows, not raise an AttributeError.
def test_format_schedule_csv_returns_empty_rows_when_items_attribute_missing():
    # Arrange
    schedule_view = types.SimpleNamespace()

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert
    assert headers == EXPECTED_HEADERS
    assert rows == []


# TC-CSV-003
# An object with an empty 'items' list must also produce zero rows.
def test_format_schedule_csv_returns_empty_rows_for_empty_items_list():
    # Arrange
    schedule_view = types.SimpleNamespace(items=[])

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert
    assert headers == EXPECTED_HEADERS
    assert rows == []


# TC-CSV-004
# Items must be sorted by date ascending in the output rows, regardless of
# the order they appear in the input list.
def test_format_schedule_csv_sorts_items_by_date():
    # Arrange
    later = _make_item(date="2026-06-05", title="Later Course")
    earlier = _make_item(date="2026-06-01", title="Earlier Course")
    schedule_view = types.SimpleNamespace(items=[later, earlier])

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert
    assert [row[0] for row in rows] == ["2026-06-01", "2026-06-05"]
    assert [row[1] for row in rows] == ["Earlier Course", "Later Course"]


# TC-CSV-005
# A falsy instructor value must fall back to the em-dash placeholder
# instead of an empty string.
def test_format_schedule_csv_falls_back_to_dash_for_missing_instructor():
    # Arrange
    item = _make_item(instructor="")
    schedule_view = types.SimpleNamespace(items=[item])

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert
    assert rows[0][2] == "—"


# TC-CSV-006
# A real instructor name must be passed through unchanged.
def test_format_schedule_csv_keeps_real_instructor_name():
    # Arrange
    item = _make_item(instructor="Dr. Mizrahi")
    schedule_view = types.SimpleNamespace(items=[item])

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert
    assert rows[0][2] == "Dr. Mizrahi"


# TC-CSV-007
# The subtitle's HTML must be stripped: '<br>' becomes a newline separator
# (then a space when joined into Details), embedded tags (e.g. <span>) are
# removed entirely, and the 'ID: ' prefix is dropped from the course-id part.
def test_format_schedule_csv_strips_html_and_id_prefix_from_subtitle():
    # Arrange
    item = _make_item(
        subtitle="ID: 10101<br><span style='color: #0f766e;'>Prog 83101 (Obligatory)</span>",
        tooltip="Calculus 1 (10101)\n2026-06-01 · FALL · Moed ALEPH\nInstructor: Dr. Cohen · EXAM\nProg 83101 (Obligatory)",
    )
    schedule_view = types.SimpleNamespace(items=[item])

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert
    details = rows[0][3]
    assert "ID: " not in details
    assert "<span" not in details
    assert "<br>" not in details
    assert "10101" in details
    programs = rows[0][4]
    assert programs == "Prog 83101 (Obligatory)"


# TC-CSV-008
# When the tooltip's second line carries a ' · ' separated meta segment,
# that segment must be appended to the Details column after the course ID.
def test_format_schedule_csv_appends_tooltip_metadata_to_details():
    # Arrange
    item = _make_item(
        subtitle="ID: 10101<br>Prog 83101 (Obligatory)",
        tooltip="Calculus 1 (10101)\n2026-06-01 · FALL · Moed ALEPH\nInstructor: Dr. Cohen · EXAM\nProg 83101 (Obligatory)",
        evaluation="",
    )
    schedule_view = types.SimpleNamespace(items=[item])

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert — "10101" followed by the meta piece taken after the first ' · '.
    assert rows[0][3] == "10101 · FALL · Moed ALEPH"


# TC-CSV-009
# When the evaluation type is present, it must be appended to the Details
# column as a final ' · <EVAL>' suffix, after any tooltip metadata.
def test_format_schedule_csv_appends_evaluation_type_to_details():
    # Arrange
    item = _make_item(
        subtitle="ID: 10101<br>Prog 83101 (Obligatory)",
        tooltip="Calculus 1 (10101)\n2026-06-01 · FALL · Moed ALEPH\nInstructor: Dr. Cohen · EXAM\nProg 83101 (Obligatory)",
        evaluation="EXAM",
    )
    schedule_view = types.SimpleNamespace(items=[item])

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert
    assert rows[0][3] == "10101 · FALL · Moed ALEPH · EXAM"


# TC-CSV-010
# When there are no remaining subtitle parts after the course-id line, the
# Programs column must fall back to the em-dash placeholder rather than an
# empty string.
def test_format_schedule_csv_falls_back_to_dash_for_missing_programs():
    # Arrange — subtitle has only the "ID: " line, no program lines after it.
    item = _make_item(subtitle="ID: 10101", tooltip="Calculus 1 (10101)\n")
    schedule_view = types.SimpleNamespace(items=[item])

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert
    assert rows[0][4] == "—"


# TC-CSV-011
# Multiple remaining subtitle parts (multiple <br>-separated program lines)
# must be joined into the Programs column with newlines, preserving order.
def test_format_schedule_csv_joins_multiple_program_lines_with_newline():
    # Arrange
    item = _make_item(
        subtitle="ID: 10101<br>Prog 83101 (Obligatory)<br>Prog 83102 (Elective)",
        tooltip="Calculus 1 (10101)\n2026-06-01 · FALL · Moed ALEPH\n",
    )
    schedule_view = types.SimpleNamespace(items=[item])

    # Act
    headers, rows = format_schedule_csv(schedule_view)

    # Assert
    assert rows[0][4] == "Prog 83101 (Obligatory)\nProg 83102 (Elective)"
