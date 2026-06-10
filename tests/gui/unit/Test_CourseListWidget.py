import pytest
from PyQt6.QtWidgets import QLabel
from src.gui.common.components.CourseListWidget import CourseListWidget
from src.application.viewmodels.ProgramViewModel import ProgramCoursesViewModel, CourseRowViewModel

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-CL-001: test course list empty state.
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
# TC-CL-002: test course list rendering with program block and course rows.
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
# TC-CL-003: test course list expanding a program block
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
# TC-CL-004: test course list collapsing an expanded program block.
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
# TC-CL-005: test reject case: expanding non-existent program ID behaves gracefully.
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
# TC-CL-006: test reject case: program block with empty course list handles gracefully.
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