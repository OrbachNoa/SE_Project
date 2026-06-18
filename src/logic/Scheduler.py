from typing import List, Optional, Tuple
from src.models.ExamSchedule import ExamSchedule, ExamAssignment
from .SlotBuilder import Slot
from .checkers.IConflictChecker import IConflictChecker
from .observers.IScheduleObserver import IScheduleObserver

# One remaining slot paired with its live domain: the candidate dates that
# are still consistent with every assignment placed so far. Forward checking
# narrows this list as the search descends; backtracking restores it.
_Domain = Tuple[Slot, List]


class Scheduler:
    """Builds valid schedules with backtracking, forward checking, and a
    most-constrained-variable (MRV) heuristic.

    Invariant: every domain handed to _backtrack contains only dates that are
    already consistent with the current schedule. _forward_check is the single
    place that enforces it, so _backtrack never re-validates a date it is about
    to try - it just places it.
    """

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

        # Establish the invariant once against the empty schedule. From here on
        # _backtrack keeps it true for every recursive call.
        domains = self._forward_check(
            [(slot, list(slot.candidateDates)) for slot in slots], schedule
        )
        if domains is None:
            return

        # Uses a list for the counter to pass it by reference during recursion.
        found_count = [0]
        self._backtrack(domains, schedule, observer, found_count, max_results)

    def _forward_check(self, domains: List[_Domain], schedule: ExamSchedule) -> Optional[List[_Domain]]:
        """Returns the domains keeping only dates still consistent with the
        current schedule, or None if any slot is left with no options (a dead
        end). The same checker.check() that validates a placement decides
        consistency, so this only ever drops dates that are truly unreachable -
        it never discards a date some valid completion still needs.

        A single scratch ExamAssignment is reused across all the dates of a
        slot (mutating only its date) instead of allocating one per candidate.
        Checkers only read the assignment, never store it, so this is safe and
        cuts object churn in the hottest loop of the whole search.
        """
        checkers = self._checkers
        narrowed: List[_Domain] = []
        for slot, candidate_dates in domains:
            probe = ExamAssignment(
                course=slot.course, date=None, moed=slot.moed, semester=slot.semester
            )
            surviving = []
            for d in candidate_dates:
                probe.date = d
                if not any(checker.check(probe, schedule) for checker in checkers):
                    surviving.append(d)
            if not surviving:
                return None
            narrowed.append((slot, surviving))
        return narrowed

    def _select_most_constrained(self, domains: List[_Domain]) -> int:
        """MRV: returns the index of the slot with the fewest remaining
        candidate dates, so the search tries the hardest exam first and
        fails (or succeeds) sooner.
        """
        best_index = 0
        best_size = len(domains[0][1])
        for i in range(1, len(domains)):
            size = len(domains[i][1])
            if size < best_size:
                best_index, best_size = i, size
        return best_index

    def _backtrack(
        self,
        domains: List[_Domain],
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
        if not domains:
            # This schedule will keep changing during backtracking.
            # The observer must copy or convert it now if it wants to keep this result.
            observer.on_schedule_found(schedule)
            found_count[0] += 1
            return

        chosen_index = self._select_most_constrained(domains)
        slot, candidate_dates = domains[chosen_index]
        rest = domains[:chosen_index] + domains[chosen_index + 1:]

        # Every date here is already known consistent (the invariant), so we
        # place it directly without re-checking.
        for exam_date in candidate_dates:
            # A deeper recursive call may have already reached the result limit.
            if found_count[0] >= max_results:
                return
            # Check cancellation inside the loop too, because the loop can be long.
            if observer.should_cancel():
                return

            assignment = ExamAssignment(
                course=slot.course, date=exam_date, moed=slot.moed, semester=slot.semester
            )
            schedule.addAssignment(assignment)

            # Propagate this choice into the remaining slots' domains. If it
            # empties any of them, this branch is a dead end and we skip it.
            narrowed_rest = self._forward_check(rest, schedule)
            if narrowed_rest is not None:
                self._backtrack(narrowed_rest, schedule, observer, found_count, max_results)

            # Remove the assignment before trying the next possible date.
            schedule.pop_last_assignment()
