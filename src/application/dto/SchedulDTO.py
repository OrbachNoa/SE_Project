"""Picklable transport DTOs for schedules crossing the process boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(slots=True)
class AssignmentDTO:
    """One course's exam placement, flattened to display-ready strings."""

    # Course identifier
    course_id: str

    # Human-readable course name
    course_name: str

    instructor: str

    # ISO date string of the exam
    date: str

    # Semester value. example: "FALL"
    semester: str

    # Moed value. example: "ALEPH"
    moed: str


@dataclass(slots=True)
class ScheduleDTO:
    """One candidate schedule - an ordered list of assignments."""

    # The placements making up this schedule
    assignments: List[AssignmentDTO] = field(default_factory=list)

    # Cached count of assignments
    total_assignments: int = 0