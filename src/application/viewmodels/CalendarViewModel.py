"""View models for the year-calendar rendering of a schedule.

Cells reuse ScheduleItemViewModel so calendar and list views share one item
representation. Fields are primitives or lists of view models.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .ScheduleViewModel import ScheduleItemViewModel


@dataclass
class CalendarCellViewModel:
    """A single calendar day cell."""

    # ISO date string of the exam
    date: str
    # The schedule items that fall on this date.
    items: List[ScheduleItemViewModel] = field(default_factory=list)
    # always False from a schedule alone (no exclusion data)
    is_blocked: bool = False
    # A string to show on hover, e.g. "2 exams" or "1 exam, 1 class". Empty if no items.
    tooltip: str = ""


@dataclass
class CalendarViewModel:
    """The full set of populated day cells for one schedule."""

    cells: List[CalendarCellViewModel] = field(default_factory=list)