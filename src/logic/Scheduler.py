from typing import List
from src.models.ExamSchedule import ExamSchedule, ExamAssignment
from .SlotBuilder import Slot
from .checkers.IConflictChecker import IConflictChecker
from .observers.IScheduleObserver import IScheduleObserver


class Scheduler:
    """Builds valid schedules with backtracking."""

    def __init__(self, checkers: List[IConflictChecker]):
        # Each checker represents one rule that a schedule must not break.
        self._checkers = checkers

    def generateSchedules(self, slots: List[Slot], observer: IScheduleObserver, max_results: int = 1_000_000) -> None:
        """Runs the search and streams valid schedules via observer."""
        if not slots:
            return

        # Stop early if any slot has no dates, so useless recursion is avoided.
        if any(not slot.candidateDates for slot in slots):
            return

        schedule = ExamSchedule()
        
        # Uses a list for the counter to pass it by reference during recursion.
        found_count = [0]
        self._backtrack(0, slots, schedule, observer, found_count, max_results)

    def _backtrack(
        self, 
        index: int, 
        slots: List[Slot], 
        schedule: ExamSchedule, 
        observer: IScheduleObserver, 
        found_count: List[int], 
        max_results: int
    ) -> None:
        
        # Checks cancellation on every iteration to stop recursion immediately if the user clicked cancel.
        if observer.should_cancel():
            return
            
        # Stop searching after the requested number of schedules was found.
        if found_count[0] >= max_results:
            return

        # If every slot was assigned, the current schedule is a complete valid schedule.
        if index == len(slots):
            # This schedule will keep changing during backtracking.
            # The observer must copy or convert it now if it wants to keep this result.
            observer.on_schedule_found(schedule)
            found_count[0] += 1
            return

        slot = slots[index]
        # Try each allowed date for the current exam slot.
        for date in slot.candidateDates:
            # A deeper recursive call may have already reached the result limit.
            if found_count[0] >= max_results:
                return
            # Check cancellation inside the loop too, because the loop can be long.
            if observer.should_cancel():
                return
            assignment = ExamAssignment(
                course=slot.course, date=date, moed=slot.moed, semester=slot.semester
            )

            # Check all conflict rules, so only valid assignments are kept.
            conflict = False
            for checker in self._checkers:
                if checker.check(assignment, schedule):
                    conflict = True
                    break

            # If no checker found a conflict, continue with this assignment.
            if not conflict:
                schedule.addAssignment(assignment)
                self._backtrack(index + 1, slots, schedule, observer, found_count, max_results)
                # Remove the assignment before trying the next possible date.
                schedule.pop_last_assignment()
