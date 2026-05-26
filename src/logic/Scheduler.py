from typing import List
from ..models.exam_schedule import ExamSchedule, ExamAssignment
from .SlotBuilder import Slot
from .IConflictChecker import IConflictChecker


class Scheduler:
    """
    Pure backtracking search engine.

    Consumes a list of self-contained Slots (each carrying its own
    candidate dates) and a list of conflict checkers. Knows nothing
    about courses, programs, exam periods, or how slots were built.
    Performs no precomputation on the checkers - the caller is
    responsible for preparing both inputs.

    This decoupling means the algorithm is generic and testable in
    isolation against synthetic slots.
    """

    def __init__(self, checkers: List[IConflictChecker]):
        self._checkers = checkers

    def generateSchedules(self, slots: List[Slot], max_results: int = 1_000_000) -> List[ExamSchedule]:
        """
        Runs the backtracking search over the given slots. Returns every
        valid schedule found, up to max_results.
        """
        if not slots:
            return []

        # Fast-path: if any slot has zero candidates, no schedule can include
        # it, so the whole problem is infeasible. Stop before any recursion.
        if any(not s.candidateDates for s in slots):
            return []

        schedule = ExamSchedule()
        results: List[ExamSchedule] = []
        self._backtrack(0, slots, schedule, results, max_results)
        return results

    def _backtrack(self, index: int, slots: List[Slot],
                   schedule: ExamSchedule, results: list, max_results: int) -> None:
        # Stop recursion early if max_results was reached.
        if len(results) >= max_results:
            return

        # Base case: every slot has an assignment - save a snapshot. Deep-copy
        # the date index so later backtracking mutations don't corrupt the
        # saved result.
        if index == len(slots):
            new_sched = ExamSchedule()
            new_sched.assignments = list(schedule.assignments)
            results.append(new_sched)
            return

        slot = slots[index]
        # Read candidates directly from the slot - no lookup, no period_map.
        for date in slot.candidateDates:
            if len(results) >= max_results:
                return

            assignment = ExamAssignment(
                course=slot.course, date=date, moed=slot.moed, semester=slot.semester
            )

            # Direct loop instead of any() with a generator, avoiding generator
            # overhead in the hot path.
            conflict = False
            for ck in self._checkers:
                if ck.check(assignment, schedule):
                    conflict = True
                    break

            if not conflict:
                schedule.addAssignment(assignment)
                self._backtrack(index + 1, slots, schedule, results, max_results)
                schedule.removeAssignment(assignment)