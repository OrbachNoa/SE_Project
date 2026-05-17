from typing import List, Tuple
from ..models.exam_schedule import ExamSchedule, ExamAssignment
from ..models.enums import Moed, Requirement

class Slot:
    def __init__(self, course, semester, moed):
        self.course   = course
        self.semester = semester
        self.moed     = moed

class Scheduler:

    def __init__(self, courses: list, periods: list, conflictCheckers: list,
                 validators: list, selected_programs: List[str] = None):
        self._courses           = courses
        self._periods           = periods
        self._checkers          = conflictCheckers
        self._validators        = validators
        self._selected_programs = selected_programs or []


    def filterCourses(self) -> list:
        selected_set = set(self._selected_programs)
        return [
            c for c in self._courses
            if c.hasExam() and (
                not selected_set or
                any(e.programId in selected_set for e in c.programEntries)
            )
        ]

    def _periodExists(self, semester, moed) -> bool:
        return any(p.semester == semester and p.moed == moed for p in self._periods)

    def _score(self, course) -> int:
        selected_set = set(self._selected_programs)
        score = 0
        for e in course.programEntries:
            if not selected_set or e.programId in selected_set:
                score += 1
                if e.requirement == Requirement.OBLIGATORY:
                    score += 2
        return score

    def _buildSlots(self) -> List[Slot]:
        selected_set = set(self._selected_programs)
        slots, seen  = [], set()
        for course in self.filterCourses():
            semesters = {
                e.semester for e in course.programEntries
                if not selected_set or e.programId in selected_set
            }
            for sem in semesters:
                moeds_with_period = [m for m in Moed if self._periodExists(sem, m)]
                if not moeds_with_period:
                    raise ValueError(
                        f"Course '{course.name}' ({course.courseId}) belongs to "
                        f"semester {sem.name} but no exam period is defined for "
                        f"that semester. Cannot generate a schedule that includes "
                        f"all required courses."
                    )
                for moed in moeds_with_period:
                    key = (course.courseId, sem, moed)
                    if key not in seen:
                        seen.add(key)
                        slots.append(Slot(course, sem, moed))
        slots.sort(key=lambda s: self._score(s.course), reverse=True)
        return slots

    def _getCandidates(self, slot: Slot) -> List[Tuple]:
        for period in self._periods:
            if period.semester == slot.semester and period.moed == slot.moed:
                if hasattr(period, 'getAvailableDates') and callable(period.getAvailableDates):
                    dates = period.getAvailableDates()
                    if dates:
                        return [(d,) for d in dates]
        return []


    def _backtrack(self, index: int, slots: List[Slot], candidates_cache: List[List[Tuple]], 
                   schedule: ExamSchedule, results: list, max_results: int) -> None:

        if len(results) >= max_results:
            return

        if index == len(slots):
            new_sched = ExamSchedule()
            new_sched.assignments = list(schedule.assignments)
            results.append(new_sched)
            return

        slot = slots[index]

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
                schedule.addAssignment(assignment)
                self._backtrack(index + 1, slots, candidates_cache, schedule, results, max_results)
                schedule.removeAssignment(assignment)


    def generateAllSchedules(self, max_results: int = 1000000) -> list:
        slots = self._buildSlots()
        if not slots:
            return []

        candidates_cache = []
        for slot in slots:
            candidates_cache.append(self._getCandidates(slot))

        py_checker = None
        for ck in self._checkers:
            if type(ck).__name__ == "ProgramYearConflictChecker":
                py_checker = ck
                break
                
        if py_checker and hasattr(py_checker, 'precompute_conflicts'):
            courses_set = {s.course for s in slots}
            py_checker.precompute_conflicts(list(courses_set), self._selected_programs)

        schedule = ExamSchedule()
        results  = []
        
        self._backtrack(0, slots, candidates_cache, schedule, results, max_results)
        
        return results
