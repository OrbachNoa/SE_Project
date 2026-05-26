from typing import List, Set, Tuple
from datetime import date
from ..models.enums import Moed, Requirement
from ..models.course import Course
from ..models.exam_period import ExamPeriod


class Slot:
    """
    A single exam event that needs to be scheduled, fully self-contained:
    it carries the course identity (course, semester, moed) AND the list
    of legal candidate dates for that slot. The Scheduler can consume a
    Slot without consulting any external state.
    """

    def __init__(self, course: Course, semester, moed, candidateDates: List[date]):
        self.course = course
        self.semester = semester
        self.moed = moed
        # Candidate dates come from the matching ExamPeriod's pre-filtered
        # list. Multiple slots in the same period share the same list object
        # by reference - no data duplication.
        self.candidateDates = candidateDates


class SlotBuilder:
    """
    Translates the domain (courses, programs, periods) into a flat,
    prioritized list of self-contained scheduling slots.

    Each produced Slot carries its own candidate dates, so the consumer
    (the Scheduler) does not need a reference to the periods list. This
    keeps the Scheduler a generic backtracking engine with no domain
    dependencies.

    Responsibilities:
      - Filter courses relevant to the selected programs.
      - Generate slots for every (course, semester, moed) combination
        that has a matching exam period.
      - Attach the period's available dates to each slot.
      - Order slots by 'most constrained first' so backtracking finds
        infeasibilities early.
    """

    def __init__(self, periods: List[ExamPeriod], selected_programs: List[str] = None):
        # The period_map lives only here now - the Scheduler does not need it.
        self._period_map = {(p.semester, p.moed): p for p in periods}
        # Cache the selected-programs set once, reused by all filter/score methods.
        self._selected_set: Set[str] = set(selected_programs) if selected_programs else set()

    def build(self, courses: List[Course]) -> List[Slot]:
        """
        Builds the full slot list, with candidate dates attached and ordered
        for efficient backtracking.
        """
        slots = self._buildRaw(courses)
        slots.sort(key=self._score, reverse=True)
        return slots

    def _buildRaw(self, courses: List[Course]) -> List[Slot]:
        """
        Generates the raw slot list. One slot per (course, semester, moed)
        combination, with candidate dates from the matching period.
        """
        slots: List[Slot] = []

        for course in self._filterRelevantCourses(courses):
            semesters = {
                e.semester for e in course.programEntries
                if not self._selected_set or e.programId in self._selected_set
            }
            for sem in semesters:
                periods_for_sem = [(m, self._period_map[(sem, m)])
                                   for m in Moed if (sem, m) in self._period_map]
                # Fail loudly if a course belongs to a semester that has no
                # exam period - schedules including it can never be produced.
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
        """
        Keeps courses that have an exam and belong to at least one selected
        program. When no programs are selected, every course with an exam passes.
        """
        return [
            c for c in courses
            if c.hasExam() and (
                not self._selected_set or
                any(e.programId in self._selected_set for e in c.programEntries)
            )
        ]

    def _score(self, slot: Slot) -> int:
        """
        Heuristic: courses that are obligatory and/or shared across many
        selected programs get higher scores. Higher score => scheduled
        earlier => conflicts surface faster during backtracking.
        """
        score = 0
        for e in slot.course.programEntries:
            if not self._selected_set or e.programId in self._selected_set:
                score += 1
                if e.requirement == Requirement.OBLIGATORY:
                    score += 2
        return score