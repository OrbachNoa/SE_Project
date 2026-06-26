"""Unit tests for CalendarEditorWidget — the per-period date-exclusion editor.

The widget composes a date-range picker, a PeriodNavigator, and a
CalendarWidget grid to let the user step through each ExamPeriod and toggle
individual dates as excluded. Tests cover initial rendering from the first
period's view model, that editing the start date writes back into the
underlying PeriodEditViewModel, that toggling a calendar cell updates both
the model and the cell's style, navigation between periods, the
apply_and_get_constraints() round trip, the construction-time guard against
an empty period list, and that an invalid date range (start after end)
clears the grid instead of rendering a corrupt one.

Conventions:
- Each test carries a unique TC-CEW-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections.
- Tests use the shared `qapp` fixture (tests/conftest.py) via
  `pytestmark = pytest.mark.usefixtures("qapp")`; PeriodEditViewModel has no
  conftest fixture, so each test builds its own list of view models.
"""
import pytest
from PyQt6.QtCore import QDate
from src.gui.common.components.CalendarEditorWidget import CalendarEditorWidget
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-CEW-001: constructing with a list of periods must render the first
# period's date range and label immediately, with navigation buttons
# reflecting that there is nowhere to go back to yet.
# ===========================================================================
def test_calendar_editor_initial_state():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=["2026-06-02"]
        ),
        PeriodEditViewModel(
            semester="FALL",
            moed="BET",
            start_date="2026-07-01",
            end_date="2026-07-03",
            excluded_dates=[]
        )
    ]
    
    # Act
    widget = CalendarEditorWidget(vms)
    
    # Assert
    assert widget.start_date_edit.date() == QDate(2026, 6, 1)
    assert widget.end_date_edit.date() == QDate(2026, 6, 3)
    assert "Semester FALL - Moed ALEPH (1/2)" in widget.period_label.text()
    assert widget.prev_btn.isEnabled() is False
    assert widget.next_btn.isEnabled() is True

# ===========================================================================
# TC-CEW-002: editing the start date in the UI must write through to the
# underlying PeriodEditViewModel — the widget is not allowed to keep its
# own disconnected copy of the date that diverges from the model.
# ===========================================================================
def test_calendar_editor_date_change():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=[]
        )
    ]
    widget = CalendarEditorWidget(vms)
    
    # Act
    widget.start_date_edit.setDate(QDate(2026, 6, 2))
    
    # Assert
    assert widget._model.start_date == "2026-06-02"

# ===========================================================================
# TC-CEW-003: toggling a date must update both the model's excluded_dates
# list and the corresponding cell's object name — the visual state and the
# data the editor will save must never disagree.
# ===========================================================================
def test_calendar_editor_cell_toggle():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=[]
        )
    ]
    widget = CalendarEditorWidget(vms)
    
    # Act
    widget.toggle_date_exclusion("2026-06-03")
    
    # Assert
    assert "2026-06-03" in widget._model.excluded_dates
    assert widget.calendar_grid._day_frames["2026-06-03"].objectName() == "calendar-cell-excluded"

# ===========================================================================
# TC-CEW-004: clicking next must switch the editor to the next period's
# data (label, model index) and update the prev/next button enabled state
# to match the new position — not just move an internal counter.
# ===========================================================================
def test_calendar_editor_navigation_next():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=[]
        ),
        PeriodEditViewModel(
            semester="FALL",
            moed="BET",
            start_date="2026-07-01",
            end_date="2026-07-03",
            excluded_dates=[]
        )
    ]
    widget = CalendarEditorWidget(vms)
    
    # Act
    widget.next_btn.click()
    
    # Assert
    assert widget._model.current_index == 1
    assert "Semester FALL - Moed BET (2/2)" in widget.period_label.text()
    assert widget.prev_btn.isEnabled() is True
    assert widget.next_btn.isEnabled() is False

# ===========================================================================
# TC-CEW-005: clicking prev after having moved forward must return the
# editor to the first period exactly — confirms backward navigation is
# wired, not just that next disables itself once at the end.
# ===========================================================================
def test_calendar_editor_navigation_prev():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=[]
        ),
        PeriodEditViewModel(
            semester="FALL",
            moed="BET",
            start_date="2026-07-01",
            end_date="2026-07-03",
            excluded_dates=[]
        )
    ]
    widget = CalendarEditorWidget(vms)
    widget.next_btn.click()
    
    # Act
    widget.prev_btn.click()
    
    # Assert
    assert widget._model.current_index == 0
    assert widget.prev_btn.isEnabled() is False
    assert widget.next_btn.isEnabled() is True

# ===========================================================================
# TC-CEW-006: apply_and_get_constraints() must return periods carrying the
# exclusions made through the UI, and those same exclusions must already
# be reflected on the original view models passed in — the caller should
# not need a separate save step to persist what was toggled.
# ===========================================================================
def test_calendar_editor_apply():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=[]
        )
    ]
    widget = CalendarEditorWidget(vms)
    widget.toggle_date_exclusion("2026-06-02")
    
    # Act
    returned_periods = widget.apply_and_get_constraints()
    
    # Assert
    assert len(returned_periods) == 1
    assert returned_periods[0].excluded_dates == ["2026-06-02"]
    assert vms[0].excluded_dates == ["2026-06-02"]

# ===========================================================================
# TC-CEW-007: constructing the editor with zero periods must raise
# ValueError immediately — there is no valid "empty" editor state to fall
# back to, since ExclusionModel itself requires at least one period.
# ===========================================================================
def test_calendar_editor_empty_periods_reject():
    # Arrange
    empty_vms = []
    
    # Act & Assert
    with pytest.raises(ValueError, match="ExclusionModel requires at least one period."):
        CalendarEditorWidget(empty_vms)

# ===========================================================================
# TC-CEW-008: setting a start date after the end date must clear the
# calendar grid rather than rendering a grid built from an inverted,
# nonsensical range.
# ===========================================================================
def test_calendar_editor_invalid_date_range_clears_calendar():
    # Arrange
    vms = [
        PeriodEditViewModel(
            semester="FALL",
            moed="ALEPH",
            start_date="2026-06-01",
            end_date="2026-06-03",
            excluded_dates=[]
        )
    ]
    widget = CalendarEditorWidget(vms)
    
    # Act
    widget.start_date_edit.setDate(QDate(2026, 6, 10))
    
    # Assert
    assert len(widget.calendar_grid._day_frames) == 0
