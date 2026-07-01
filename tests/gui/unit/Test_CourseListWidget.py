"""
Test suite for CourseListWidget.

Scope   : The collapsible program-row logic — a rendered program block starts
          collapsed and clicking its header reveals (then re-hides) its course
          rows. This is the widget's only real interactive behaviour and backs
          a user flow (browsing the loaded courses per program), so it is
          driven through a real header-button click.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CLW-001
Fixtures: qapp (tests/conftest.py)
"""
from types import SimpleNamespace

import pytest

from src.gui.common.components.CourseListWidget import CourseListWidget

pytestmark = pytest.mark.usefixtures("qapp")


def _course():
    return SimpleNamespace(
        course_id="10001", course_name="Algorithms", instructor="Dr. Cohen",
        year=1, semester="A", requirement="Obligatory",
        evaluation="Exam", is_exam_relevant=True,
    )


def _program():
    return SimpleNamespace(
        program_id="83101", program_name="Software Engineering",
        courses=[_course()],
    )


# ===========================================================================
# TC-CLW-001: a rendered program block must start collapsed (its course rows
# hidden) and toggle visibility on each header click — expand on the first
# click, collapse on the second.
# ===========================================================================
def test_course_list_program_block_expands_and_collapses_on_click():
    # Arrange
    widget = CourseListWidget()
    widget.render([_program()])
    block = widget._blocks["83101"]

    # Act — courses start hidden; a header click expands them, another collapses.
    # isHidden() reflects the explicit local hidden flag, independent of whether
    # the (unshown) top-level widget has a visible ancestor.
    hidden_initially = block._body.isHidden()
    block._header_btn.click()
    hidden_after_expand = block._body.isHidden()
    block._header_btn.click()
    hidden_after_collapse = block._body.isHidden()

    # Assert
    assert hidden_initially is True
    assert hidden_after_expand is False
    assert hidden_after_collapse is True
