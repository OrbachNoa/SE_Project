"""Unified overlay calendar widget for two-family schedule comparison.

Extends CalendarWidget to accept colour-annotated exam items.  Each item carries
a ``source`` tag:

  - ``"family_a"`` → badge uses a magenta/pink border (unique to Family A)
  - ``"family_b"`` → badge uses a neon-green border (unique to Family B)
  - ``"mutual"``   → badge uses a warm cream / gold border (same slot in both)

The widget is a drop-in replacement for OutputCalendarWidget in the overlay
screen: callers call ``display_overlay_assignments(items_with_source)`` instead
of ``display_assignments``.
"""
from __future__ import annotations

from typing import List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from gui.common.components.OutputCalendarWidget import OutputCalendarWidget
from src.application.viewmodels.ScheduleViewModel import ScheduleItemViewModel


class OverlayCalendarWidget(OutputCalendarWidget):
    """Calendar grid that renders per-family colour-coded exam badges."""

    def display_overlay_assignments(
        self,
        items: List[Tuple[ScheduleItemViewModel, str]],
    ) -> None:
        """Place colour-coded exam tiles into day cells.

        Parameters
        ----------
        items:
            List of ``(ScheduleItemViewModel, source)`` where *source* is one of
            ``"family_a"``, ``"family_b"``, or ``"mutual"``.
        """
        for item, source in items:
            target_date = item.date
            if target_date not in self._day_layouts:
                continue

            # Build the badge body from structured fields instead of parsing the
            # pre-composed subtitle HTML.
            detail_lines = [item.course_id] if item.course_id else []
            detail_lines.extend(item.programs)
            body = "\n".join(detail_lines)

            title_prefix = "mutual " if source == "mutual" else ""
            exam_label = QLabel(f"{title_prefix}{item.title}\n{body}")
            exam_label.setWordWrap(True)
            exam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            exam_label.setToolTip(item.tooltip)

            if source == "family_a":
                obj_name = "overlay-badge-a"
            elif source == "family_b":
                obj_name = "overlay-badge-b"
            else:
                obj_name = "overlay-badge-mutual"

            exam_label.setObjectName(obj_name)
            self._day_layouts[target_date].addWidget(exam_label)
