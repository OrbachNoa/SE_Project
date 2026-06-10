"""Calendar widget variant used for rendered schedules."""
from __future__ import annotations

from gui.common.components.CalendarWidget import CalendarWidget

# This is a specialized version of the calendar built specifically for the final results screen.
# It inherits all the main drawing and layout features from the original CalendarWidget we looked at earlier.
class OutputCalendarWidget(CalendarWidget):
    """Calendar grid with output-only styling for excluded period dates."""

    # Applies a specific visual style to a day box to show that it was blocked off (excluded).
    # It uses a unique "output" style tag, so these boxes might look slightly different (e.g., solid gray) compared to the interactive input editor.
    def set_date_excluded_output_style(self, date_str: str) -> None:
        self._set_date_object_name(date_str, "calendar-cell-excluded-output")