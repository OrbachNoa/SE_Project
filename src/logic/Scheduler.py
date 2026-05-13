"""
scheduler.py
------------
Scheduler — orchestrates the backtracking search that produces all valid
ExamSchedule objects for the selected programs.

Design notes
------------
* "Slot" = one (course, semester, moed) triple.  A course taught in two
  semesters creates two independent slots; a slot covers both Aleph and
  Bet moeds for that semester (one slot per moed).
* Slots are sorted hardest-first before the search begins, so the most
  constrained assignments are tried earliest → faster pruning.
* The backtracking is pure: add → recurse → remove.  No global state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import copy


# ---------------------------------------------------------------------------
# Internal data class — a schedulable unit
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Slot:
    """
    An atomic unit of scheduling work.

    One Course can generate multiple Slots when it appears in more than
    one (semester, moed) combination across its program entries.
    """
    course:   object   # Course
    semester: object   # Semester enum value
    moed:     object   # Moed enum value


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Generates every conflict-free ExamSchedule for the chosen programs.

    Parameters
    ----------
    courses : List[Course]
        All courses parsed from the courses file.
    periods : List[ExamPeriod]
        All exam periods parsed from the periods file.
    selected_programs : List[int]
        The program IDs chosen by the user (up to 5).
    conflict_checkers : List[IConflictChecker]
        Pluggable conflict-checking strategies (open/closed principle).
    """

    def __init__(
        self,
        courses:           list,
        periods:           list,
        conflictCheckers:  list,
        validators:        list,
        selected_programs: List[int] = None,
    ):
        self._courses           = courses
        self._periods           = periods
        self._checkers          = conflictCheckers
        self._validators        = validators
        self._selected_programs = selected_programs or []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generateAllSchedules(self) -> list:
        """
        Entry point.  Returns a list of all valid ExamSchedule objects.
        Each schedule assigns exactly one (date, moed) to every relevant slot.
        """
        # Step 1 — build and sort slots
        slots = self._buildSlots()

        # Step 2 — run backtracking
        from models import ExamSchedule  # local import to avoid circularity
        schedule = ExamSchedule()
        results: list = []
        self._backtrack(0, slots, schedule, results)
        return results

    def filterCourses(self) -> list:
        """
        Returns only the courses that:
          1. Belong to at least one selected program.
          2. Have evaluation == EXAM (hasExam() == True).
        """
        relevant: list = []
        selected_set = set(self._selected_programs)

        for course in self._courses:
            if not course.has_exam():
                continue
            # Keep if any program entry belongs to a selected program
            for entry in course.program_entries:
                if entry.program_id in selected_set:
                    relevant.append(course)
                    break

        return relevant

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _buildSlots(self) -> List[Slot]:
        """
        Convert filtered courses into Slot objects, one per
        (course, semester, moed) combination.

        Example: a course in FALL only generates slots:
            (course, FALL, ALEPH)
            (course, FALL, BET)

        Slots are then sorted hardest-first using _score().
        """
        from models import Moed  # local import

        relevant_courses = self.filterCourses()
        selected_set     = set(self._selected_programs)
        slots: List[Slot] = []

        seen: set = set()  # deduplicate (courseId, semester, moed)

        for course in relevant_courses:
            semesters_for_course: set = set()

            for entry in course.program_entries:
                if entry.program_id in selected_set:
                    semesters_for_course.add(entry.semester)

            for semester in semesters_for_course:
                for moed in Moed:
                    # Only create a slot if there is a matching period
                    if self._periodExists(semester, moed):
                        key = (course.courseId, semester, moed)
                        if key not in seen:
                            seen.add(key)
                            slots.append(Slot(course=course, semester=semester, moed=moed))

        # Sort hardest-first (descending score) for better pruning
        slots.sort(key=lambda s: self._score(s.course), reverse=True)
        return slots

    def _periodExists(self, semester, moed) -> bool:
        """True if there is an ExamPeriod for (semester, moed)."""
        for period in self._periods:
            if period.semester == semester and period.moed == moed:
                return True
        return False

    def _score(self, course) -> int:
        """
        Static difficulty heuristic for a course.

        +1 for each program the course belongs to (more programs → more
           potential conflicts)
        +2 if the course is OBLIGATORY in any of those programs (obligatory
           courses create hard conflicts; elective–elective clashes are allowed)

        Higher score → schedule this course's slot earlier in the search.
        """
        from models import Requirement  # local import

        score = 0
        selected_set = set(self._selected_programs)

        for entry in course.program_entries:
            if entry.program_id in selected_set:
                score += 1
                if entry.requirement == Requirement.OBLIGATORY:
                    score += 2

        return score

    def _getCandidates(self, slot: Slot) -> List[Tuple]:
        """
        Return all (date,) pairs available for this slot's (semester, moed).
        Delegates to ExamPeriod.get_available_dates().
        """
        candidates: List[Tuple] = []

        for period in self._periods:
            if period.semester == slot.semester and period.moed == slot.moed:
                for date in period.get_available_dates():
                    candidates.append((date,))
                break  # only one period per (semester, moed)

        return candidates

    def _backtrack(
        self,
        index:   int,
        slots:   List[Slot],
        schedule,
        results: list,
    ) -> None:
        """
        Core recursive backtracking procedure.

        Base case  : index == len(slots) → all slots assigned → save snapshot.
        Recursive  : try every candidate date for slots[index]; for each that
                     passes all checkers, add to schedule, recurse, then remove.
        """
        from models import ExamAssignment  # local import

        # ── Base case ──────────────────────────────────────────────────
        if index == len(slots):
            # Deep-copy so that subsequent mutations don't corrupt saved schedules
            results.append(copy.deepcopy(schedule))
            return

        slot = slots[index]

        # ── Try every candidate date ───────────────────────────────────
        for (date,) in self._getCandidates(slot):
            assignment = ExamAssignment(
                course   = slot.course,
                date     = date,
                moed     = slot.moed,
                semester = slot.semester,
            )

            # Run all conflict checkers (short-circuits on first failure)
            if not any(checker.check(assignment, schedule) for checker in self._checkers):
                schedule.addAssignment(assignment)
                self._backtrack(index + 1, slots, schedule, results)
                schedule.removeAssignment(assignment)   # backtrack
    
def run_pipeline(courses, periods, selected_programs, conflictCheckers, validators):
    scheduler = Scheduler(
        courses=courses,
        periods=periods,
        conflictCheckers=conflictCheckers,
        validators=validators,
        selected_programs=selected_programs,
    )
    return scheduler.generateAllSchedules()