from typing import List
from models.ExamSchedule import ExamSchedule, ExamAssignment
from .SlotBuilder import Slot
from .checkers.IConflictChecker import IConflictChecker
from .observers.IScheduleObserver import IScheduleObserver


class Scheduler:
    """Builds valid schedules with backtracking."""

    def __init__(self, checkers: List[IConflictChecker]):
        self._checkers = checkers

    def generateSchedules(self, slots: List[Slot], observer: IScheduleObserver, max_results: int = 1_000_000) -> None:
        """Runs the search and streams valid schedules via observer."""
        if not slots:
            return

        # Stop early if any slot has no dates, so useless recursion is avoided.
        if any(not s.candidateDates for s in slots):
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
            
        # Stop recursion early if max_results was reached.
        if found_count[0] >= max_results:
            return

        # Stream a schedule when every slot was assigned.
        if index == len(slots):
            # Passes the original schedule directly because the Observer immediately maps it to a safe DTO.
            # This saves CPU cycles by avoiding unnecessary object and list copying.
            observer.on_schedule_found(schedule)
            found_count[0] += 1
            
            # Updates progress every 10 schedules to prevent flooding the IPC queue and GUI thread.
            if found_count[0] % 10 == 0:
                observer.on_progress(found_count[0])
                
            return

        slot = slots[index]
        # Use slot dates directly, so no period lookup is needed.
        for date in slot.candidateDates or observer.should_cancel():
            # Check maximum results inside the loop because a deep branch might have reached the limit.
            if found_count[0] >= max_results:
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

            # Proceed with the recursive search because no checker found a conflict.
            if not conflict:
                schedule.addAssignment(assignment)
                self._backtrack(index + 1, slots, schedule, observer, found_count, max_results)
                schedule.removeAssignment(assignment)
