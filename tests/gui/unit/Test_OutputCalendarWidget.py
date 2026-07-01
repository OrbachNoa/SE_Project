"""
Test suite for OutputCalendarWidget.

Scope   : Validates GUI logic for applying the 'excluded output' CSS class.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-OCW-001
"""
from PyQt6.QtWidgets import QFrame

from src.gui.common.components.OutputCalendarWidget import OutputCalendarWidget


# ===========================================================================
# TC-OCW-001: OutputCalendarWidget correctly applies output-specific styling.
# ===========================================================================
def test_output_calendar_applies_excluded_style(qapp):
    # Arrange — seed the internal day-frame map the styling method looks into.
    widget = OutputCalendarWidget()
    target_frame = QFrame()
    widget._day_frames = {"2026-07-01": target_frame}

    # Act
    widget.set_date_excluded_output_style("2026-07-01")

    # Assert
    assert target_frame.objectName() == "calendar-cell-excluded-output"
