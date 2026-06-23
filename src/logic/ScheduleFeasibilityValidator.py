from __future__ import annotations

from typing import List, Optional

from src.logic.SlotBuilder import Slot
from src.logic.checkers.config.CheckerFactory import build_checkers
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig
from src.logic.feasibility.FeasibilityContext import FeasibilityContext
from src.logic.feasibility.FeasibilityRule import FeasibilityRule
from src.logic.feasibility.MandatorySpanGapRule import MandatorySpanGapRule
from src.logic.feasibility.MoedOrderDomainRule import MoedOrderDomainRule
from src.logic.feasibility.NonEmptyDomainRule import NonEmptyDomainRule


class ScheduleFeasibilityValidator:
    """Runs conservative preflight checks before scheduler backtracking starts.

    Structural rules (no candidate dates, broken moed order) have no matching
    checker, so they stay as standalone FeasibilityRule instances. Threshold
    rules (min gap, max per day, elective cap, exam span) reuse the same
    IConflictChecker built by build_checkers, so the capacity-bound logic
    lives in one place alongside the matching pairwise conflict check.
    """

    def __init__(self, structural_rules: Optional[List[FeasibilityRule]] = None) -> None:
        self._structural_rules = structural_rules or [
            NonEmptyDomainRule(),
            MoedOrderDomainRule(),
            MandatorySpanGapRule(),
        ]

    def validate(
        self,
        courses: list,
        selected_programs: Optional[list],
        slots: List[Slot],
        config: Optional[ConstraintsConfig],
    ) -> List[str]:
        context = FeasibilityContext(
            selected_programs=selected_programs,
            slots=slots,
            config=config,
        )

        errors: List[str] = []
        for rule in self._structural_rules:
            errors.extend(rule.validate(context))

        checkers = build_checkers(config, courses, selected_programs, slots)
        for checker in checkers:
            errors.extend(checker.feasibility_bound(context))

        return errors
