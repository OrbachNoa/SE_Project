"""View model for editing an exam period in the calendar editor."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class PeriodEditViewModel:
    """One exam period, flattened for display/editing."""

    # Semester value. example: "FALL"
    semester: str
    # Exam moed. example: "ALEPH"
    moed: str
    # Start date of the period.
    start_date: str
    # End date of the period.
    end_date: str
    # Dates excluded from the period.
    excluded_dates: List[str] = field(default_factory=list)