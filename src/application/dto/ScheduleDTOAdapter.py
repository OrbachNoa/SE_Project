from __future__ import annotations

from datetime import date

from models.enums import Moed, Semester
from application.dto.SchedulDTO import AssignmentDTO, ScheduleDTO


class _CourseView:
    """Exposes only `name` and `instructor` — the fields the writer reads."""
    __slots__ = ("name", "instructor")

    def __init__(self, name: str, instructor: str) -> None:
        self.name = name
        self.instructor = instructor


class _AssignmentView:
    """Adapts one AssignmentDTO so it presents the shape of ExamAssignment."""
    __slots__ = ("date", "semester", "moed", "course")

    def __init__(self, dto: AssignmentDTO) -> None:
        # ISO string -> date object, so strftime() works.
        self.date = date.fromisoformat(dto.date)
        # String value -> Enum, so .name lookup works.
        self.semester = Semester(dto.semester)
        self.moed = Moed(dto.moed)
        # Nested course view, so a.course.name / a.course.instructor work.
        self.course = _CourseView(dto.course_name, dto.instructor)


class ScheduleDTOAdapter:
    """Adapts a ScheduleDTO to the ExamSchedule shape expected by the writer."""
    __slots__ = ("assignments",)

    def __init__(self, dto: ScheduleDTO) -> None:
        self.assignments = [_AssignmentView(a) for a in dto.assignments]
