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
    """Detects impossible combinations of mandatory span and minimum gap.

    The individual checkers already validate each threshold by itself. This
    rule covers the cross-constraint case where the span rule forces an early
    or late mandatory exam in two moed groups, while the mandatory/all gap rule
    requires those forced exams to be farther apart than the date windows allow.
    """

    def validate(self, context: FeasibilityContext) -> List[str]:
        config = context.config
        if config is None or config.exam_span is None or config.exam_span <= 0:
            return []

        gap = self._mandatory_gap(config)
        if gap is None or gap <= 0:
            return []

        groups = self._mandatory_groups(context)
        extremes_by_group = {
            key: self._possible_span_extremes(slots, config.exam_span)
            for key, slots in groups.items()
            if len(slots) >= 2 and all(slot.candidateDates for slot in slots)
        }

        # Note: the minimum-gap rule (2.1/2.2) applies across the whole
        # (program, year) cohort regardless of semester, so groups from
        # different semesters are still compared against each other here even
        # though the span rule (2.4) itself is scoped per semester.
        errors: List[str] = []
        groups_by_cohort: Dict[
            Tuple[str, int], List[Tuple[object, object, Tuple[List[date], List[date]]]]
        ] = defaultdict(list)
        for (program_id, year, semester, moed), extremes in extremes_by_group.items():
            possible_min_dates, possible_max_dates = extremes
            if possible_min_dates and possible_max_dates:
                groups_by_cohort[(program_id, year)].append((semester, moed, extremes))

        for (program_id, year), sem_moed_groups in groups_by_cohort.items():
            for i, (left_semester, left_moed, left_extremes) in enumerate(sem_moed_groups):
                for right_semester, right_moed, right_extremes in sem_moed_groups[i + 1:]:
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
        gaps = [
            value for value in (config.min_gap_obligatory, config.min_gap_any)
            if value is not None
        ]
        return max(gaps) if gaps else None

    def _mandatory_groups(
        self, context: FeasibilityContext
    ) -> Dict[Tuple[str, int, object, object], Set[Slot]]:
        selected = context.selected_set
        groups: Dict[Tuple[str, int, object, object], Set[Slot]] = defaultdict(set)
        for slot in context.slots:
            for entry in slot.course.programEntries:
                if selected and entry.programId not in selected:
                    continue
                if entry.requirement is not Requirement.OBLIGATORY:
                    continue
                if entry.semester != slot.semester:
                    continue
                groups[(entry.programId, entry.year, slot.semester, slot.moed)].add(slot)
        return groups

    def _possible_span_extremes(
        self, slots: Set[Slot], span: int
    ) -> Tuple[List[date], List[date]]:
        ordered_slots = list(slots)
        min_by_slot = [min(slot.candidateDates) for slot in ordered_slots]
        max_by_slot = [max(slot.candidateDates) for slot in ordered_slots]
        possible_min_dates: Set[date] = set()
        possible_max_dates: Set[date] = set()

        for index, slot in enumerate(ordered_slots):
            other_min = min(
                min_date for pos, min_date in enumerate(min_by_slot)
                if pos != index
            )
            other_max = max(
                max_date for pos, max_date in enumerate(max_by_slot)
                if pos != index
            )
            for candidate in slot.candidateDates:
                if (other_max - candidate).days >= span:
                    possible_min_dates.add(candidate)
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
        comparisons = (
            ("earliest", left_extremes[0], "earliest", right_extremes[0]),
            ("earliest", left_extremes[0], "latest", right_extremes[1]),
            ("latest", left_extremes[1], "earliest", right_extremes[0]),
            ("latest", left_extremes[1], "latest", right_extremes[1]),
        )

        for left_label, left_dates, right_label, right_dates in comparisons:
            if not left_dates or not right_dates:
                continue
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
        return all(
            abs((left_date - right_date).days) < gap
            for left_date in left_dates
            for right_date in right_dates
        )
