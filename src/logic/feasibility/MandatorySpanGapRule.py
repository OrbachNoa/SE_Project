from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Set, Tuple

from src.logic.SlotBuilder import Slot
from src.logic.feasibility.FeasibilityContext import FeasibilityContext
from src.logic.feasibility.FeasibilityRule import FeasibilityRule
from src.logic.feasibility.helpers import enum_name
from src.models.Enums import Requirement


class MandatorySpanGapRule(FeasibilityRule):
    """
    Detects impossible combination between mandatory exam span and minimum gap.

    The regular checkers already check each rule by itself.
    This rule checks the case where two rules together make the schedule impossible.

    Example:
    The exam span rule can force one mandatory exam to be very early or very late.
    At the same time, the minimum gap rule requires mandatory exams to be far enough
    from each other.
    If every possible option is still too close, there is no valid schedule.
    """

    def validate(self, context: FeasibilityContext) -> List[str]:
        """
        Fast pre-check before the full search.

        The goal is to catch cases where mandatory span and minimum gap cannot
        both be satisfied together.
        """

        # Take the constraints config from the context.
        config = context.config

        # If there is no exam span rule, this rule has nothing to check.
        if config is None or config.exam_span is None or config.exam_span <= 0:
            return []

        # Get the relevant mandatory gap from the config.
        gap = self._mandatory_gap(config)

        # If there is no mandatory gap rule, this rule has nothing to check.
        if gap is None or gap <= 0:
            return []

        # Build all mandatory groups by program, year, semester and moed.
        groups = self._mandatory_groups(context)

        # For each group, calculate which dates can be forced as earliest/latest
        # while still satisfying the required exam span.
        extremes_by_group = {
            key: self._possible_span_extremes(slots, config.exam_span)
            for key, slots in groups.items()
            if len(slots) >= 2 and all(slot.candidateDates for slot in slots)
        }

        # Save the messeges if we get impossible assignment.
        errors: List[str] = []

        # Key: program and year.
        # Value: semester/moed span groups for that program/year.
        groups_by_cohort: Dict[
            Tuple[str, int], List[Tuple[object, object, Tuple[List[date], List[date]]]]
        ] = defaultdict(list)

        # Add only groups that have at least one possible earliest date
        # and at least one possible latest date.
        for (program_id, year, semester, moed), extremes in extremes_by_group.items():
            possible_min_dates, possible_max_dates = extremes
            if possible_min_dates and possible_max_dates:
                groups_by_cohort[(program_id, year)].append((semester, moed, extremes))

        # Compare every pair of semester/moed groups in the same program/year.
        for (program_id, year), sem_moed_groups in groups_by_cohort.items():
            for i, (left_semester, left_moed, left_extremes) in enumerate(sem_moed_groups):
                for right_semester, right_moed, right_extremes in sem_moed_groups[i + 1:]:
                    # Check if the forced earliest/latest exams from both groups are always too close to each other.
                    error = self._forced_extreme_gap_error(
                        program_id,
                        year,
                        left_semester,
                        left_moed,
                        left_extremes,
                        right_semester,
                        right_moed,
                        right_extremes,
                        gap,
                        config.exam_span,
                    )

                    if error is not None:
                        errors.append(error)
                        break

        return errors

    def _mandatory_gap(self, config) -> Optional[int]:
        """
        Return the gap that obligatory exam pairs must satisfy.

        If both obligatory-gap and any-gap are enabled, obligatory pairs must satisfy
        both rules, so we use the larger value.
        """

        # Take only gap values that really exist.
        gaps = [
            value for value in (config.min_gap_obligatory, config.min_gap_any)
            if value is not None
        ]

        # Return the strictest gap, or None if there is no gap rule.
        return max(gaps) if gaps else None

    def _mandatory_groups(
        self, context: FeasibilityContext
    ) -> Dict[Tuple[str, int, object, object], Set[Slot]]:
        """
        Build the mandatory exam groups that the span rule applies to.

        Each group contains obligatory exam slots from the same program, year,
        semester and moed, because the mandatory span rule is checked only inside
        that exact academic group.
        """

        # Take the programs that the user selected.
        selected = context.selected_set

        # Dict that groups mandatory slots by program/year/semester/moed.
        groups: Dict[Tuple[str, int, object, object], Set[Slot]] = defaultdict(set)

        # Go over all slots that can be scheduled.
        for slot in context.slots:
            for entry in slot.course.programEntries:
                # Ignore programs that are not selected.
                if selected and entry.programId not in selected:
                    continue

                # Take only obligatory courses.
                if entry.requirement is not Requirement.OBLIGATORY:
                    continue

                # The entry must match the semester of the slot.
                if entry.semester != slot.semester:
                    continue

                # Add this slot to the relevant group.
                groups[(entry.programId, entry.year, slot.semester, slot.moed)].add(slot)

        return groups

    def _possible_span_extremes(
        self, slots: Set[Slot], span: int
    ) -> Tuple[List[date], List[date]]:
        """
        Find which dates can be the earliest or latest exam in this group.

        A date can be earliest if there is another exam that can be at least span
        days after it.

        A date can be latest if there is another exam that can be at least span
        days before it.
        """

        # Convert set to list so every slot has stable index in this calculation.
        ordered_slots = list(slots)

        # For each slot, save its earliest possible date.
        min_by_slot = [min(slot.candidateDates) for slot in ordered_slots]

        # For each slot, save its latest possible date.
        max_by_slot = [max(slot.candidateDates) for slot in ordered_slots]

        # Dates that can be used as the first exam in the span.
        possible_min_dates: Set[date] = set()

        # Dates that can be used as the last exam in the span.
        possible_max_dates: Set[date] = set()

        for index, slot in enumerate(ordered_slots):
            # Earliest date among all other slots.
            other_min = min(
                min_date for pos, min_date in enumerate(min_by_slot)
                if pos != index
            )

            # Latest date among all other slots.
            other_max = max(
                max_date for pos, max_date in enumerate(max_by_slot)
                if pos != index
            )

            for candidate in slot.candidateDates:
                # Candidate can be the earliest date if another slot can be
                # at least span days after it.
                if (other_max - candidate).days >= span:
                    possible_min_dates.add(candidate)

                # Candidate can be the latest date if another slot can be
                # at least span days before it.
                if (candidate - other_min).days >= span:
                    possible_max_dates.add(candidate)

        return sorted(possible_min_dates), sorted(possible_max_dates)

    def _forced_extreme_gap_error(
        self,
        program_id: str,
        year: int,
        left_semester,
        left_moed,
        left_extremes: Tuple[List[date], List[date]],
        right_semester,
        right_moed,
        right_extremes: Tuple[List[date], List[date]],
        gap: int,
        span: int,
    ) -> Optional[str]:
        """
        Check whether two mandatory span groups cannot coexist because of the gap rule.

        Each group may need an earliest and latest exam to satisfy its own span rule.
        This method checks whether every possible combination of these edge dates is
        closer than the required minimum gap.
        """

        # All combinations of forced extreme dates that need to be checked.
        comparisons = (
            ("earliest", left_extremes[0], "earliest", right_extremes[0]),
            ("earliest", left_extremes[0], "latest", right_extremes[1]),
            ("latest", left_extremes[1], "earliest", right_extremes[0]),
            ("latest", left_extremes[1], "latest", right_extremes[1]),
        )

        for left_label, left_dates, right_label, right_dates in comparisons:
            # If one side has no dates, there is nothing to compare.
            if not left_dates or not right_dates:
                continue

            # If every possible pair is closer than the required gap,
            # then these two groups cannot both satisfy the rules.
            if self._every_pair_is_too_close(left_dates, right_dates, gap):
                return (
                    f"Exam span {span} days combined with minimum gap {gap} days "
                    f"is infeasible for program {program_id} year {year}: "
                    f"the {left_label} {enum_name(left_semester)} {enum_name(left_moed)} "
                    f"mandatory exam and the {right_label} {enum_name(right_semester)} "
                    f"{enum_name(right_moed)} mandatory exam would always be too close."
                )

        return None

    def _every_pair_is_too_close(
        self, left_dates: List[date], right_dates: List[date], gap: int
    ) -> bool:
        """
        Return True if every date pair from both lists is closer than gap days.
        """

        # Check every possible date from left side with every possible date from right side.
        return all(
            abs((left_date - right_date).days) < gap
            for left_date in left_dates
            for right_date in right_dates
        )