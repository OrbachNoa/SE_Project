"""Unit tests for CalendarWidget and its OutputCalendarWidget subclass.

CalendarWidget builds a per-date grid of cells from a plain list of date
strings, then lets callers attach exam badges (display_assignments) or mark
cells excluded/included for the period editor. OutputCalendarWidget reuses
the same grid but applies its own object-name styling for excluded dates on
the read-only output screen. Tests cover grid construction and clearing,
badge content/formatting, and that exclusion styling sets the expected Qt
object name (which the stylesheet keys off) rather than just an internal flag.

Conventions:
- Each test carries a unique TC-CW-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections.
- Tests use the shared `qapp` fixture (tests/conftest.py) via
  `pytestmark = pytest.mark.usefixtures("qapp")`; no other conftest fixture
  applies to this widget's plain construction.
"""
import pytest
from PyQt6.QtWidgets import QLabel
from src.gui.common.components.CalendarWidget import CalendarWidget
from src.gui.common.components.OutputCalendarWidget import OutputCalendarWidget
from src.application.viewmodels.ScheduleViewModel import ScheduleItemViewModel

pytestmark = pytest.mark.usefixtures("qapp")

# ===========================================================================
# TC-CW-001: setup_month_grid must create one layout and one frame per date
# given, and show the month banner with the correct month/year text.
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
# TC-CW-002: rebuilding the grid with an empty date list must clear the
# previous month's cells, not just stop adding new ones — otherwise a
# month-to-month navigation would leak stale cells.
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
# TC-CW-003: display_assignments must add the exam badge as a second item
# in the day's layout (after the day-number label) and tag it with the
# "calendar-exam-badge" object name the stylesheet relies on.
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
# TC-CW-004: the badge's displayed text must show the course title plus a
# cleaned-up subtitle — the "ID: " prefix and "<br>" HTML tag from the
# view-model subtitle are stripped/converted, not shown raw.
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
# TC-CW-005: marking a date excluded must set the cell frame's object name
# to "calendar-cell-excluded" — the stylesheet has no other way to detect
# exclusion, since it never reads the underlying boolean directly.
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
# TC-CW-006: re-including a previously-excluded date must reset the cell
# frame's object name to "calendar-cell-included" — the toggle has to be
# reversible, not a one-way style change.
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
# TC-CW-007: OutputCalendarWidget uses its own "-output" suffixed object
# name for excluded dates, distinct from the editor's styling, so the
# read-only output screen can be styled independently of the editor.
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
