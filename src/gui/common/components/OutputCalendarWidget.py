"""Calendar widget variant used for rendered schedules."""
from __future__ import annotations

from gui.common.components.CalendarWidget import CalendarWidget


class OutputCalendarWidget(CalendarWidget):
    """Calendar grid with output-only styling for excluded period dates."""

    def set_date_excluded_output_style(self, date_str: str) -> None:
        self._set_date_object_name(date_str, "calendar-cell-excluded-output")
