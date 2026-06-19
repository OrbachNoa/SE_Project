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

    def __init__(self, checkers: List[IConflictChecker], collect_checker_stats: bool = False):
        # Each checker represents one rule that a schedule must not break.
        self._checkers = checkers
        # Opt-in only: per-checker call/reject counters, used to measure which
        # checker actually prunes the search (rejection rate) so checkers can be
        # ordered by how often they short-circuit any(). Off by default because
        # it replaces the any() short-circuit in _forward_check - the hottest
        # loop in the search - with an explicit loop; real runs should pay
        # nothing for a measurement nobody is reading.
        self._collect_checker_stats = collect_checker_stats
        if collect_checker_stats:
            self._checker_calls = [0] * len(checkers)
            self._checker_rejects = [0] * len(checkers)

    def get_checker_stats(self) -> List[dict]:
        """Per-checker call/reject counts gathered since this Scheduler was
        created, in the same order as the checkers list. Empty when
        collect_checker_stats was not enabled.
        """
        if not self._collect_checker_stats:
            return []
        stats = []
        for checker, calls, rejects in zip(self._checkers, self._checker_calls, self._checker_rejects):
            stats.append({
                "name": type(checker).__name__,
                "scope": getattr(checker, "_scope", None).value if getattr(checker, "_scope", None) else None,
                "k": getattr(checker, "_k", None),
                "calls": calls,
                "rejects": rejects,
            })
        return stats

    def generateSchedules(
        self,
        slots: List[Slot],
        observer: IScheduleObserver,
        max_results: int = 1_000_000,
        target_depth: Optional[int] = None,
        seed_assignments: Optional[List[ExamAssignment]] = None,
        use_mrv: bool = True,
    ) -> None:
        """Runs the search and streams valid schedules via observer.

        The optional parameters power cube-and-conquer parallelism without
        changing the default behavior (omit them all to get exactly today's
        full MRV search):

        - target_depth: stop and report once this many slots are assigned. None
          means len(slots), i.e. only complete schedules are reported (today's
          behavior). A smaller value turns the same search into a cube
          generator that emits *partial* schedules of that depth.
        - seed_assignments: a list of already-validated assignments to pre-load
          (aligned to the leading slots), so a worker resumes from a partial
          schedule instead of rebuilding it. The search continues with the
          slots after the seed.
        - use_mrv: when True (default) each step picks the most-constrained
          slot. Cube generation passes False to assign slots in their fixed
          (leading-index) order, so every cube is a prefix over slots[0..K-1] -
          this keeps the cubes disjoint and complete, which is what makes the
          seed dates align to the leading slot indices.
        """
        if not slots:
            return

        # Stop early if any slot has no dates, so useless recursion is avoided.
        if any(not slot.candidateDates for slot in slots):
            return

        if target_depth is None:
            target_depth = len(slots)

        schedule = ExamSchedule()

        # Pre-load the seed (already validated by the partitioner) without
        # re-running checkers; the search then resumes from the slots after it.
        if seed_assignments:
            for assignment in seed_assignments:
                schedule.addAssignment(assignment)
            remaining_slots = slots[len(seed_assignments):]
        else:
            remaining_slots = slots

        # Establish the invariant once against the current (possibly seeded)
        # schedule. From here on _backtrack keeps it true for every call.
        domains = self._forward_check(
            [(slot, list(slot.candidateDates)) for slot in remaining_slots], schedule
        )
        if domains is None:
            return

        # Uses a list for the counter to pass it by reference during recursion.
        found_count = [0]
        self._backtrack(domains, schedule, observer, found_count, max_results, target_depth, use_mrv)

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
        if self._collect_checker_stats:
            calls, rejects = self._checker_calls, self._checker_rejects
            for slot, candidate_dates in domains:
                probe = ExamAssignment(
                    course=slot.course, date=None, moed=slot.moed, semester=slot.semester
                )
                surviving = []
                for d in candidate_dates:
                    probe.date = d
                    # Explicit loop (instead of any()) so each checker's call/
                    # reject count is attributed correctly, while still
                    # stopping at the first rejection like any() would.
                    rejected = False
                    for i, checker in enumerate(checkers):
                        calls[i] += 1
                        if checker.check(probe, schedule):
                            rejects[i] += 1
                            rejected = True
                            break
                    if not rejected:
                        surviving.append(d)
                if not surviving:
                    return None
                narrowed.append((slot, surviving))
            return narrowed

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
        max_results: int,
        target_depth: int,
        use_mrv: bool,
    ) -> None:

        # Checks cancellation on every iteration to stop recursion immediately if the user clicked cancel.
        if observer.should_cancel():
            return

        # Stop searching after the requested number of schedules was found.
        if found_count[0] >= max_results:
            return

        # Once target_depth slots are assigned, report the schedule. For a full
        # search this is the complete schedule (today's behavior); for cube
        # generation it is a partial schedule of the requested depth.
        if len(schedule.assignments) == target_depth:
            # This schedule will keep changing during backtracking.
            # The observer must copy or convert it now if it wants to keep this result.
            observer.on_schedule_found(schedule)
            found_count[0] += 1
            return

        # MRV for real search; fixed leading-index order for cube generation.
        chosen_index = self._select_most_constrained(domains) if use_mrv else 0
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
                self._backtrack(narrowed_rest, schedule, observer, found_count, max_results, target_depth, use_mrv)

            # Remove the assignment before trying the next possible date.
            schedule.pop_last_assignment()
