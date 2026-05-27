from typing import List
from ..models.exam_schedule import ExamSchedule, ExamAssignment
from .SlotBuilder import Slot
from .IConflictChecker import IConflictChecker


class Scheduler:
    """Builds valid schedules with backtracking."""

    def __init__(self, checkers: List[IConflictChecker]):
        self._checkers = checkers

    def generateSchedules(self, slots: List[Slot], max_results: int = 1_000_000) -> List[ExamSchedule]:
        """Runs the search and returns valid schedules."""
        if not slots:
            return []

        # Stop early if any slot has no dates, so useless recursion is avoided.
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

        # Save a schedule when every slot was assigned.
        if index == len(slots):
            new_sched = ExamSchedule()
            new_sched.assignments = list(schedule.assignments)
            results.append(new_sched)
            return

        slot = slots[index]
        # Use slot dates directly, so no period lookup is needed.
        for date in slot.candidateDates:
            if len(results) >= max_results:
                return

            assignment = ExamAssignment(
                course=slot.course, date=date, moed=slot.moed, semester=slot.semester
            )

            # Check all conflict rules, so only valid assignments are kept.
            conflict = False
            for ck in self._checkers:
                if ck.check(assignment, schedule):
                    conflict = True
                    break

            if not conflict:
                schedule.addAssignment(assignment)
                self._backtrack(index + 1, slots, schedule, results, max_results)
                schedule.removeAssignment(assignment)
