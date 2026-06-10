"""View models for presenting study programs and their courses."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CourseRowViewModel:
    """One course as shown within a program's course list."""

    course_id: str
    course_name: str
    year: int
    # Semester value. example: "FALL"
    semester: str
    # OBLIGATORY / ELECTIVE
    requirement: str
    # EXAM / PROJECT / ATTENDANCE
    evaluation: str
    instructor: str
    # only exam courses get scheduled
    is_exam_relevant: bool


@dataclass
class ProgramViewModel:
    """A one-line summary of a program for the selector widget."""

    program_id: str
    display_name: str
    # exam-bearing courses only
    course_count: int = 0


@dataclass
class ProgramCoursesViewModel:
    """A program together with its expanded list of course rows."""

    program_id: str
    # A human-readable name for the program.
    program_name: str
    courses: List[CourseRowViewModel] = field(default_factory=list)