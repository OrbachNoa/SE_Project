import pytest
from PyQt6.QtWidgets import QLabel
from src.gui.common.components.CalendarWidget import CalendarWidget
from src.gui.common.components.OutputCalendarWidget import OutputCalendarWidget
from src.application.viewmodels.ScheduleViewModel import ScheduleItemViewModel

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-CW-001: test grid construction.
# ===========================================================================
def test_calendar_widget_grid_construction():
    # Arrange
    widget = CalendarWidget()
    dates = ["2026-06-01", "2026-06-02", "2026-06-03"]
    
    # Act
    widget.setup_month_grid(dates, show_month_header=False, show_month_banner=True)
    
    # Assert
    assert len(widget._day_layouts) == 3
    assert len(widget._day_frames) == 3
    assert "2026-06-01" in widget._day_layouts
    assert not widget.month_lbl.isHidden()
    assert "June 2026" in widget.month_lbl.text()

# ===========================================================================
# TC-CW-002: test grid clearing when empty list is passed.
# ===========================================================================
def test_calendar_widget_grid_clearing():
    # Arrange
    widget = CalendarWidget()
    dates = ["2026-06-01", "2026-06-02", "2026-06-03"]
    widget.setup_month_grid(dates, show_month_header=False, show_month_banner=True)
    
    # Act
    widget.setup_month_grid([], show_month_header=False, show_month_banner=True)
    
    # Assert
    assert len(widget._day_layouts) == 0
    assert len(widget._day_frames) == 0

# ===========================================================================
# TC-CW-003: test display_assignments constructs badge widget in layout.
# ===========================================================================
def test_calendar_widget_display_assignments_adds_badge_to_layout():
    # Arrange
    widget = CalendarWidget()
    dates = ["2026-06-01"]
    widget.setup_month_grid(dates, show_month_header=False, show_month_banner=False)
    
    item = ScheduleItemViewModel(
        date="2026-06-01",
        title="Software Engineering",
        subtitle="ID: 83-311<br>Moed A",
        tooltip="SE exam details"
    )
    
    # Act
    widget.display_assignments([item])
    
    # Assert
    # A label for the day number and a label for the exam
    layout = widget._day_layouts["2026-06-01"]
    assert layout.count() == 2
    # Check that the exam widget is a QLabel and has the correct object name
    exam_widget = layout.itemAt(1).widget()
    assert isinstance(exam_widget, QLabel)
    assert exam_widget.objectName() == "calendar-exam-badge"

# ===========================================================================
# TC-CW-004: test display_assignments formats subtitle text (strips ID and tags).
# ===========================================================================
def test_calendar_widget_display_assignments_formats_text():
    # Arrange
    widget = CalendarWidget()
    dates = ["2026-06-01"]
    widget.setup_month_grid(dates, show_month_header=False, show_month_banner=False)
    
    item = ScheduleItemViewModel(
        date="2026-06-01",
        title="Software Engineering",
        subtitle="ID: 83-311<br>Moed A",
        tooltip="SE exam details"
    )
    
    # Act
    widget.display_assignments([item])
    
    # Assert
    layout = widget._day_layouts["2026-06-01"]
    exam_widget = layout.itemAt(1).widget()
    assert "Software Engineering" in exam_widget.text()
    assert "83-311\nMoed A" in exam_widget.text()
    assert "ID: " not in exam_widget.text()

# ===========================================================================
# TC-CW-005: test set date excluded style updates frame object name.
# ===========================================================================
def test_calendar_widget_exclusion_style_when_excluded():
    # Arrange
    widget = CalendarWidget()
    dates = ["2026-06-01"]
    widget.setup_month_grid(dates, show_month_header=False, show_month_banner=False)
    
    # Act
    widget.set_date_excluded_style("2026-06-01", is_excluded=True)
    
    # Assert
    assert widget._day_frames["2026-06-01"].objectName() == "calendar-cell-excluded"

# ===========================================================================
# TC-CW-006: test set date included style updates frame object name.
# ===========================================================================
def test_calendar_widget_exclusion_style_when_included():
    # Arrange
    widget = CalendarWidget()
    dates = ["2026-06-01"]
    widget.setup_month_grid(dates, show_month_header=False, show_month_banner=False)
    
    # Act
    widget.set_date_excluded_style("2026-06-01", is_excluded=False)
    
    # Assert
    assert widget._day_frames["2026-06-01"].objectName() == "calendar-cell-included"

# ===========================================================================
# TC-CW-007: test OutputCalendarWidget custom styling.
# ===========================================================================
def test_output_calendar_widget_styles():
    # Arrange
    widget = OutputCalendarWidget()
    dates = ["2026-06-01"]
    widget.setup_month_grid(dates, show_month_header=False, show_month_banner=False)
    
    # Act
    widget.set_date_excluded_output_style("2026-06-01")
    
    # Assert
    assert widget._day_frames["2026-06-01"].objectName() == "calendar-cell-excluded-output"
