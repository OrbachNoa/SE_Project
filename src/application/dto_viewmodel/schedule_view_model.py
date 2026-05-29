"""View models for displaying a single exam schedule.

ScheduleItemViewModel holds pre-composed display strings (the mapper does the
composing) so widgets render them verbatim. Fields are primitives only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ScheduleItemViewModel:
    """One exam, flattened to display-ready strings."""

    # ISO date string of the exam
    date: str
    # Course name
    title: str
    # Course id / semester / moed
    subtitle: str
    # Full hover text
    tooltip: str


@dataclass
class ScheduleViewModel:
    """A schedule's items plus "X of Y" navigation context (for example, "Schedule 2 of 5" when browsing alternatives)."""

    # The items to display
    items: List[ScheduleItemViewModel] = field(default_factory=list)
    current_index: int = 0
    total: int = 1

    
    # True when there are no items to display, so the UI can show an empty state instead of a blank calendar.
    def is_empty(self) -> bool:
        """True when there are no items to display."""
        return len(self.items) == 0