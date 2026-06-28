from typing import List, Optional, Tuple
from src.models.ExamSchedule import ExamSchedule, ExamAssignment
from .SlotBuilder import Slot
from .checkers.IConflictChecker import IConflictChecker
from .observers.IScheduleObserver import IScheduleObserver
from src.config import DEFAULT_MAX_RESULTS

# A domain means one unscheduled slot and the dates that are still possible for it.
_Domain = Tuple[Slot, List]
_SlotKey = Tuple[str, object, object]


class Scheduler:
    """Core search engine for building valid exam schedules.

    It tries dates with backtracking, removes impossible dates early,
    and sends every valid schedule to the observer.
    """

    def __init__(self, checkers: List[IConflictChecker]):
        # These are the rules that decide if a date is allowed or not.
        self._checkers = checkers

    def generateSchedules(
        self,
        slots: List[Slot],
        observer: IScheduleObserver,
        max_results: int = DEFAULT_MAX_RESULTS,
        target_depth: Optional[int] = None,
        seed_assignments: Optional[List[ExamAssignment]] = None,
        use_mrv: bool = True,
        scorer=None,
    ) -> None:
        """Start the schedule search and stream every valid result to the observer."""

         # No exams to schedule.
        if not slots:
            return

        # If one slot has no dates, no complete schedule can exist.
        if any(not slot.candidateDates for slot in slots):
            return

        # By default we search for full schedules, not partial ones.
        if target_depth is None:
            target_depth = len(slots)


        # Create the schedule object.
        # Date-order support is enabled only if one of the checkers needs it.
        schedule = ExamSchedule(
            use_ordinal_index=any(
                getattr(checker, "uses_ordinal_date_index", False)
                for checker in self._checkers
            )
        )

        # Keep an incremental score state only when scoring is enabled.
        score_state = scorer.create_state() if scorer is not None and hasattr(scorer, "create_state") else None

        # If this worker starts from a partial schedule, load it first.
        if seed_assignments:
            for assignment in seed_assignments:
                schedule.addAssignment(assignment)
                if score_state is not None:
                    score_state.add_assignment(assignment)

            # Continue only with the slots that were not already assigned by the seed.
            remaining_slots = self._remaining_slots_after_seed(slots, seed_assignments)
        else:
            remaining_slots = slots

        # Build the first domains and remove dates that already conflict with the seed.
        domains = self._forward_check(
            [(slot, list(slot.candidateDates)) for slot in remaining_slots], schedule
        )
        # If the seed already makes some slot impossible, stop this branch.
        if domains is None:
            return

        # Uses a list for the counter to pass it by reference during recursion.
        found_count = [0]
        # Start the recursive search.
        self._backtrack(domains, schedule, observer, found_count, max_results, target_depth, use_mrv, score_state)

    def _remaining_slots_after_seed(self, slots: List[Slot], seed_assignments: List[ExamAssignment]) -> List[Slot]:
        """Return every slot not already represented by the seed assignments."""
        seed_count = len(seed_assignments)
        if seed_count <= len(slots) and all(
            self._assignment_key(seed_assignments[i]) == self._slot_key(slots[i])
            for i in range(seed_count)
        ):
            return slots[seed_count:]

        seeded_keys = set()
        for assignment in seed_assignments:
            key = self._assignment_key(assignment)
            if key in seeded_keys:
                raise ValueError("seed_assignments contains duplicate slots")
            seeded_keys.add(key)

        matched_keys = set()
        remaining = []
        for slot in slots:
            key = self._slot_key(slot)
            if key in seeded_keys:
                matched_keys.add(key)
            else:
                remaining.append(slot)

        if matched_keys != seeded_keys:
            raise ValueError("seed_assignments contains an assignment that does not match any scheduler slot")
        return remaining

    @staticmethod
    def _slot_key(slot: Slot) -> _SlotKey:
        return (slot.course.courseId, slot.semester, slot.moed)

    @staticmethod
    def _assignment_key(assignment: ExamAssignment) -> _SlotKey:
        return (assignment.course.courseId, assignment.semester, assignment.moed)

    def _forward_check(self, domains: List[_Domain], schedule: ExamSchedule) -> Optional[List[_Domain]]:
        """Return narrowed domains, or None if some slot has no valid dates left."""
        checkers = self._checkers
        narrowed: List[_Domain] = []

        # Normal fast path: keep only dates that no checker rejects.
        for slot, candidate_dates in domains:
            # Reuse one temporary assignment instead of creating a new one for every date.
            probe = ExamAssignment(
                course=slot.course, date=None, moed=slot.moed, semester=slot.semester
            )
            surviving = []
            for d in candidate_dates:
                probe.date = d
                # If no checker rejects this date, keep it.
                rejected = False
                for checker in checkers:
                    if checker.check(probe, schedule):
                        rejected = True
                        break
                if not rejected:
                    surviving.append(d)


            # If this slot has no possible dates left, this branch cannot become a schedule.
            if not surviving:
                return None
            narrowed.append((slot, surviving))
        return narrowed

    def _select_most_constrained(self, domains: List[_Domain]) -> int:
        """Pick the slot with the fewest dates left, so bad branches fail earlier."""
        best_index = 0
        best_size = len(domains[0][1])
        # Search for the slot with the smallest remaining date list.
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
        score_state=None,
    ) -> None:
        """Recursive search: choose a slot, try each date, and go deeper."""
        # Stop quickly if the user cancelled the search.
        if observer.should_cancel():
            return

        # Do not search more than the requested result limit.
        if found_count[0] >= max_results:
            return

        # If we assigned enough slots, report the current schedule.
        # The observer must copy it now because backtracking will keep changing it.
        if len(schedule.assignments) == target_depth:
            # This schedule will keep changing during backtracking.
            # The observer must copy or convert it now if it wants to keep this result.
            if score_state is not None and hasattr(observer, "on_scored_schedule_found"):
                observer.on_scored_schedule_found(schedule, score_state.score())
            else:
                observer.on_schedule_found(schedule)
            found_count[0] += 1
            return

        # Real search uses MRV.
        # Cube generation uses fixed order so work units stay separated.
        chosen_index = self._select_most_constrained(domains) if use_mrv else 0
        # Take the chosen slot out of the remaining work.
        slot, candidate_dates = domains[chosen_index]
        rest = domains[:chosen_index] + domains[chosen_index + 1:]

        # Try every date that is still valid for this slot.
        for exam_date in candidate_dates:
            # A deeper recursive call may have already reached the result limit.
            if found_count[0] >= max_results:
                return
            # Check cancellation inside the loop too, because the loop can be long.
            if observer.should_cancel():
                return

            # Try this date by placing the assignment into the current schedule.
            assignment = ExamAssignment(
                course=slot.course, date=exam_date, moed=slot.moed, semester=slot.semester
            )
            schedule.addAssignment(assignment)
            if score_state is not None:
                score_state.add_assignment(assignment)

            # After placing this date, remove impossible dates from the remaining slots.
            narrowed_rest = self._forward_check(rest, schedule)

            # Continue only if every remaining slot still has at least one valid date.
            if narrowed_rest is not None:
                self._backtrack(narrowed_rest, schedule, observer, found_count, max_results, target_depth, use_mrv, score_state)

            # Undo this choice before trying the next date.
            if score_state is not None:
                score_state.pop_assignment()
            schedule.pop_last_assignment()
