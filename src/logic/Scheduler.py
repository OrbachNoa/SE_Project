from ast import Dict
from typing import List, Tuple
from ..models.exam_schedule import ExamSchedule, ExamAssignment
from ..models.enums import Moed, Requirement

class Slot:
    """
    Represents a single exam event that needs to be scheduled.
    """

    def __init__(self, course, semester, moed):
        self.course   = course
        self.semester = semester
        self.moed     = moed

class Scheduler:
    """
    Manages the exam scheduling process by transforming course requirements
    into a prioritized sequence of scheduling slots, precomputing constraint data,
    and executing a backtracking search to generate valid exam timetables.
    """

    def __init__(self, courses: list, periods: list, conflictCheckers: list,
                 validators: list, selected_programs: List[str] = None):
        self._courses           = courses
        self._periods           = periods
        self._checkers          = conflictCheckers
        self._validators        = validators
        # Default to an empty list if no programs are provided, so filtering logic doesn't crash.
        self._selected_programs = selected_programs or []
        # Compute once — reused by filterCourses, _buildSlots, _score, _getCandidates.
        self._selected_set = set(selected_programs) if selected_programs else set()
        # O(1) period lookup instead of O(n) scan on every call.
        self._period_map: Dict = {(p.semester, p.moed): p for p in periods}
        
        # Return only courses that have an exam and belong to the selected programs,
        # ignore all others.
    def filterCourses(self) -> list:
        return [
            c for c in self._courses
            if c.hasExam() and (
                not self._selected_set or
                any(e.programId in self._selected_set for e in c.programEntries)
            )
        ]

    def _periodExists(self, semester, moed) -> bool:
        return (semester, moed) in self._period_map

    def _score(self, course) -> int:
        score = 0
        for e in course.programEntries:
            if not self._selected_set or e.programId in self._selected_set:
                score += 1
                # Give higher weight to obligatory courses.
                if e.requirement == Requirement.OBLIGATORY:
                    score += 2
        return score

    def _buildSlots(self) -> List[Slot]:
        # Track seen combinations (course, sem, moed), so duplicate slots are not created.
        slots, seen  = [], set()
        for course in self.filterCourses():
            # Collect all relevant semesters for the course.
            semesters = {
                e.semester for e in course.programEntries
                if not self._selected_set or e.programId in self._selected_set
            }
            # For each semester, find the relevant moeds and create the combination.
            for sem in semesters:
                moeds_with_period = [m for m in Moed if self._periodExists(sem, m)]
                # Fail early if a course has no valid exam period.
                if not moeds_with_period:
                    raise ValueError(
                        f"Course '{course.name}' ({course.courseId}) belongs to "
                        f"semester {sem.name} but no exam period is defined for "
                        f"that semester. Cannot generate a schedule that includes "
                        f"all required courses."
                    )
                # Check is combination exists, otherwise create it and add it to seen.
                for moed in moeds_with_period:
                    key = (course.courseId, sem, moed)
                    if key not in seen:
                        seen.add(key)
                        slots.append(Slot(course, sem, moed))
        # Sort slots by score descending, so the backtracking tackles the hardest courses first.
        slots.sort(key=lambda s: self._score(s.course), reverse=True)
        return slots

    def _getCandidates(self, slot: Slot) -> List[Tuple]:
        p = self._period_map.get((slot.semester, slot.moed))
        if p is None:
            return []
        dates = p.availableDates
        if not dates:
            return []
        return [(d,) for d in dates]


    def _backtrack(self, index: int, slots: List[Slot], candidates_cache: List[List[Tuple]], 
                   schedule: ExamSchedule, results: list, max_results: int) -> None:

        # Stop recursion if the max limit is reached.
        if len(results) >= max_results:
            return

        # Check if all slots are scheduled, so we can save the successful board state.
        if index == len(slots):
            new_sched = ExamSchedule()
            # Copy the assignments, so further backtracking doesn't erase this successful result.
            new_sched.assignments = list(schedule.assignments)
            results.append(new_sched)
            return

        slot = slots[index]

        # Iterate over precomputed dates from the cache to avoid recalculating candidates in every step.
        for (date,) in candidates_cache[index]:
            if len(results) >= max_results:
                return

            assignment = ExamAssignment(course=slot.course, date=date, moed=slot.moed, semester=slot.semester)

            # Use a direct loop, so conflict checks avoid extra generator work.
            conflict = False
            for ck in self._checkers:
                if ck.check(assignment, schedule):
                    conflict = True
                    break

            if not conflict:
                # Add the assignment to the schedule.
                schedule.addAssignment(assignment)
                # Move forward to the next slot (recursive step).
                self._backtrack(index + 1, slots, candidates_cache, schedule, results, max_results)
                # Remove the assignment from the schedule.
                schedule.removeAssignment(assignment)

    def generateAllSchedules(self, max_results: int = 1000000) -> list:
        # Build and sort slots, creating a prioritized list of exams to schedule.
        slots = self._buildSlots()
        if not slots:
            return []

        # Precompute all candidate dates for all slots.
        candidates_cache = []
        for slot in slots:
            candidates_cache.append(self._getCandidates(slot))

        # Trigger the pre-computations once.
        py_checker = None
        for ck in self._checkers:
            if type(ck).__name__ == "ProgramYearConflictChecker":
                py_checker = ck
                break
                
        if py_checker and hasattr(py_checker, 'precompute_conflicts'):
            courses_set = {s.course for s in slots}
            py_checker.precompute_conflicts(list(courses_set), list(self._selected_set))

        # Create an empty schedule.
        schedule = ExamSchedule()
        # Create an empty list for the results.
        results  = []

        # Start the recursive backtracking process and find all valid schedules.
        self._backtrack(0, slots, candidates_cache, schedule, results, max_results)
        return results
