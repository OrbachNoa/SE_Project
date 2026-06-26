"""Unit tests for CourseListWidget — collapsible per-program course blocks.

The widget renders one collapsible block per loaded program, each holding
the program's course rows. Tests cover the placeholder shown when no
programs are loaded, that rendering builds one block per program with the
expected header text and an exam-relevant row tagged for styling, that
expand/collapse toggles both the internal flag and the body's visibility in
sync, and two reject paths: expanding an unknown program ID must be a no-op
rather than raising or expanding the wrong block, and a program with zero
courses must render its block without any course rows or group label.

Conventions:
- Each test carries a unique TC-CL-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections.
- Tests use the shared `qapp` fixture (tests/conftest.py) via
  `pytestmark = pytest.mark.usefixtures("qapp")`; ProgramCoursesViewModel
  and CourseRowViewModel have no conftest fixture, so each test builds its
  own view models directly.
"""
import pytest
from PyQt6.QtWidgets import QLabel
from src.gui.common.components.CourseListWidget import CourseListWidget
from src.application.viewmodels.ProgramViewModel import ProgramCoursesViewModel, CourseRowViewModel

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-CL-001: rendering with no programs must show the "no programs loaded"
# placeholder label — the empty state needs to be visibly different from a
# blank widget, not just an absence of content.
# ===========================================================================
def test_course_list_empty_state():
    # Arrange
    widget = CourseListWidget()

    # Act
    widget.render([])

    # Assert
    empty_label = widget.findChild(QLabel, "course-empty-lbl")
    assert empty_label is not None
    assert empty_label.text() == "No study programs loaded into context."

# ===========================================================================
# TC-CL-002: rendering a program with one exam-relevant course must build a
# collapsed block keyed by program ID, with the header showing both the ID
# and name, and a course row tagged "course-row-exam" for styling.
# ===========================================================================
def test_course_list_rendering():
    # Arrange
    widget = CourseListWidget()
    c1 = CourseRowViewModel(
        course_id="83311",
        course_name="Software Engineering",
        year=3,
        semester="FALL",
        requirement="Obligatory",
        evaluation="Exam",
        instructor="Dr. Test Instructor",
        is_exam_relevant=True
    )
    p = ProgramCoursesViewModel(
        program_id="83100",
        program_name="Computer Engineering",
        courses=[c1]
    )

    # Act
    widget.render([p])

    # Assert
    assert "83100" in widget._blocks
    block = widget._blocks["83100"]
    assert not block.isHidden()
    assert "83100" in block._header_btn.text()
    assert "Computer Engineering" in block._header_btn.text()
    assert block._expanded is False
    assert block._body.isHidden() is True

    course_row = block.findChild(object, "course-row-exam")
    assert course_row is not None

# ===========================================================================
# TC-CL-003: expand() must flip the block's expanded flag and reveal the
# body in the same call — a block that reports expanded=True with a still-
# hidden body would be a real (if subtle) UI bug.
# ===========================================================================
def test_course_list_expand():
    # Arrange
    widget = CourseListWidget()
    c1 = CourseRowViewModel(
        course_id="83311",
        course_name="Software Engineering",
        year=3,
        semester="FALL",
        requirement="Obligatory",
        evaluation="Exam",
        instructor="Dr. Test Instructor",
        is_exam_relevant=True
    )
    p = ProgramCoursesViewModel(
        program_id="83100",
        program_name="Computer Engineering",
        courses=[c1]
    )
    widget.render([p])

    # Act
    widget.expand("83100")

    # Assert
    block = widget._blocks["83100"]
    assert block._expanded is True
    assert block._body.isHidden() is False

# ===========================================================================
# TC-CL-004: collapse() must reverse expand() exactly — flag back to
# False and body hidden again — confirming the toggle round-trips instead
# of only working in one direction.
# ===========================================================================
def test_course_list_collapse():
    # Arrange
    widget = CourseListWidget()
    c1 = CourseRowViewModel(
        course_id="83311",
        course_name="Software Engineering",
        year=3,
        semester="FALL",
        requirement="Obligatory",
        evaluation="Exam",
        instructor="Dr. Test Instructor",
        is_exam_relevant=True
    )
    p = ProgramCoursesViewModel(
        program_id="83100",
        program_name="Computer Engineering",
        courses=[c1]
    )
    widget.render([p])
    widget.expand("83100")

    # Act
    widget.collapse("83100")

    # Assert
    block = widget._blocks["83100"]
    assert block._expanded is False
    assert block._body.isHidden() is True

# ===========================================================================
# TC-CL-005: expand() given a program ID that was never rendered must be a
# safe no-op — the real block must stay collapsed, not raise a KeyError or
# silently expand an unrelated block.
# ===========================================================================
def test_course_list_expand_invalid_id_reject():
    # Arrange
    widget = CourseListWidget()
    c1 = CourseRowViewModel(
        course_id="83311",
        course_name="Software Engineering",
        year=3,
        semester="FALL",
        requirement="Obligatory",
        evaluation="Exam",
        instructor="Dr. Test Instructor",
        is_exam_relevant=True
    )
    p = ProgramCoursesViewModel(
        program_id="83100",
        program_name="Computer Engineering",
        courses=[c1]
    )
    widget.render([p])

    # Act
    widget.expand("non-existent-program-id")

    # Assert
    block = widget._blocks["83100"]
    assert block._expanded is False
    assert block._body.isHidden() is True

# ===========================================================================
# TC-CL-006: a program with zero courses must still get a block (keyed by
# its ID), but that block must contain no group label and no course rows —
# rendering must not fabricate placeholder rows for missing data.
# ===========================================================================
def test_course_list_program_with_no_courses_reject():
    # Arrange
    widget = CourseListWidget()
    p = ProgramCoursesViewModel(
        program_id="83100",
        program_name="Computer Engineering",
        courses=[]
    )

    # Act
    widget.render([p])

    # Assert
    assert "83100" in widget._blocks
    block = widget._blocks["83100"]
    assert block.findChild(QLabel, "course-group-lbl") is None
    assert block.findChild(object, "course-row-exam") is None
    assert block.findChild(object, "course-row-default") is None