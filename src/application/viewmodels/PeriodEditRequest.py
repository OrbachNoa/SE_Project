"""Request DTO for editing an exam period in the calendar editor."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class PeriodEditRequest:
    """One exam period request, flattened for data transfer from UI to ViewModel.
    This class contains only primitive types and standard collections to maintain strict decoupling 
    between the presentation layer and core business logic.
    """

    # Semester value (e.g., "FALL", "SPRING")
    semester: str
    # Exam moed (e.g., "ALEPH", "BET")
    moed: str
    # Start date of the period formatted as a string (e.g., "2026-06-15")
    start_date: str
    # End date of the period formatted as a string (e.g., "2026-07-15")
    end_date: str
    # Dates excluded from the period formatted as string list (e.g., ["2026-06-20"])
    excluded_dates: List[str] = field(default_factory=list)