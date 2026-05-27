from typing import List, Set, Tuple
from datetime import date
from ..models.enums import Moed, Requirement
from ..models.course import Course
from ..models.exam_period import ExamPeriod


class Slot:
    """Stores one exam event and its possible dates."""

    def __init__(self, course: Course, semester, moed, candidateDates: List[date]):
        self.course = course
        self.semester = semester
        self.moed = moed
        # Store possible dates, so the scheduler can try them later.
        self.candidateDates = candidateDates


class SlotBuilder:
    """Builds exam slots from courses and exam periods."""

    def __init__(self, periods: List[ExamPeriod], selected_programs: List[str] = None):
        # Map each period by semester and moed, so slots can find their dates.
        self._period_map = {(p.semester, p.moed): p for p in periods}
        # Cache the selected-programs set once, reused by all filter/score methods.
        self._selected_set: Set[str] = set(selected_programs) if selected_programs else set()

    def build(self, courses: List[Course]) -> List[Slot]:
        """Builds and sorts slots for the scheduler."""
        slots = self._buildRaw(courses)
        slots.sort(key=self._score, reverse=True)
        return slots

    def _buildRaw(self, courses: List[Course]) -> List[Slot]:
        """Creates one slot for each course, semester, and moed."""
        slots: List[Slot] = []

        for course in self._filterRelevantCourses(courses):
            semesters = {
                e.semester for e in course.programEntries
                if not self._selected_set or e.programId in self._selected_set
            }
            for sem in semesters:
                periods_for_sem = [(m, self._period_map[(sem, m)])
                                   for m in Moed if (sem, m) in self._period_map]
                # Reject missing periods, so impossible schedules fail early.
                if not periods_for_sem:
                    raise ValueError(
                        f"Course '{course.name}' ({course.courseId}) belongs to "
                        f"semester {sem.name} but no exam period is defined for "
                        f"that semester. Cannot generate a schedule that includes "
                        f"all required courses."
                    )
                for moed, period in periods_for_sem:
                    slots.append(Slot(course, sem, moed, period.availableDates))
        return slots

    def _filterRelevantCourses(self, courses: List[Course]) -> List[Course]:
        """Keeps courses that need exams for the selected programs."""
        return [
            c for c in courses
            if c.hasExam() and (
                not self._selected_set or
                any(e.programId in self._selected_set for e in c.programEntries)
            )
        ]

    def _score(self, slot: Slot) -> int:
        """Scores a slot, so harder slots are scheduled earlier."""
        score = 0
        for e in slot.course.programEntries:
            if not self._selected_set or e.programId in self._selected_set:
                score += 1
                if e.requirement == Requirement.OBLIGATORY:
                    score += 2
        return score
