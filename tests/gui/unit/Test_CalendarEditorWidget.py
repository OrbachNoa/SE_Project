"""
Test suite for CalendarEditorWidget.

Scope   : The exam-period date editor's real two-way binding between the Qt
          controls and its ExclusionModel — a date picked in the UI must reach
          the period view model, and clicking a calendar day must toggle that
          date's exclusion (and notify the owning screen). These directly back
          a user flow that changes what the scheduler is allowed to do, so they
          are tested through the live widget rather than via mocks.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CEW-001, TC-CEW-002
Fixtures: qapp (tests/conftest.py)
"""
import pytest
from PyQt6.QtCore import QDate

from src.gui.common.components.CalendarEditorWidget import CalendarEditorWidget
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

pytestmark = pytest.mark.usefixtures("qapp")


def _period(start="2026-06-01", end="2026-06-10", excluded=None):
    return PeriodEditViewModel(
        semester="FALL", moed="ALEPH",
        start_date=start, end_date=end,
        excluded_dates=excluded or [],
    )


# ===========================================================================
# TC-CEW-001: picking a new start date in the date editor must flow through
# the ExclusionModel into the period view model returned on apply — proving
# the live Qt control is genuinely bound to the editable period state.
# ===========================================================================
def test_calendar_editor_date_change_updates_view_model():
    # Arrange
    vm = _period(start="2026-06-01", end="2026-06-10")
    widget = CalendarEditorWidget([vm])

    # Act — the user changes the start date; setDate fires the real dateChanged
    # signal, which syncs the controls into the model.
    widget.start_date_edit.setDate(QDate(2026, 6, 5))
    updated = widget.apply_and_get_constraints()

    # Assert — the edit landed on the period view model, not just the widget.
    assert updated[0].start_date == "2026-06-05"


# ===========================================================================
# TC-CEW-002: clicking a calendar day must toggle that date's exclusion, and
# toggling it again must remove it (reversible). Each toggle must emit
# data_changed so the input screen knows to mark its state dirty.
# ===========================================================================
def test_calendar_editor_toggles_date_exclusion_and_notifies():
    # Arrange
    widget = CalendarEditorWidget([_period(start="2026-06-01", end="2026-06-05")])
    changes = []
    widget.data_changed.connect(lambda: changes.append(1))

    # Act — exclude a date, then toggle it back off.
    widget.toggle_date_exclusion("2026-06-03")
    excluded_after_first = "2026-06-03" in widget._model.excluded_dates
    widget.toggle_date_exclusion("2026-06-03")
    excluded_after_second = "2026-06-03" in widget._model.excluded_dates

    # Assert — the exclusion is reversible and every toggle notifies the screen.
    assert excluded_after_first is True
    assert excluded_after_second is False
    assert len(changes) == 2
