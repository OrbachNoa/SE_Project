import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QDate
from src.gui.common.components.CalendarEditorWidget import CalendarEditorWidget
from src.application.viewmodels.PeriodEditViewModel import PeriodEditViewModel

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-CEW-001: test initial editor rendering and values.
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
# TC-CEW-002: test date range update syncs with model.
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
# TC-CEW-003: test calendar cell toggle updates exclusion state and style.
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
# TC-CEW-004: test period navigation forward.
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
# TC-CEW-005: test period navigation backward.
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
# TC-CEW-006: test apply returns updated constraints.
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
# TC-CEW-007: test empty periods lists raises ValueError.
# ===========================================================================
def test_calendar_editor_empty_periods_reject():
    # Arrange
    empty_vms = []
    
    # Act & Assert
    with pytest.raises(ValueError, match="ExclusionModel requires at least one period."):
        CalendarEditorWidget(empty_vms)

# ===========================================================================
# TC-CEW-008: test setting start date > end date clears calendar.
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
