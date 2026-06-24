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
    """
    Runs fast pre-checks before the scheduler starts backtracking.

    Some rules are structural rules.
    They check basic things like empty candidate dates or impossible moed order.
    These rules dont have matching conflict checker, so they are regular
    FeasibilityRule objects.

    Other rules are threshold rules.
    They check limits like min days gap, max exams per day, elective conflict cap,
    and exam span. These rules reuse the same checkers that the scheduler uses,
    so the feasibility logic stays near the conflict logic.
    """

    def __init__(self, structural_rules: Optional[List[FeasibilityRule]] = None) -> None:
        """
        Create the feasibility validator.

        If structural rules are given, use them.
        Otherwise use the default structural rules.
        """

        # Structural rules that run before the checker feasibility bounds.
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
        """
        Run all feasibility checks.

        Returns a list of error messages.
        If the list is empty, the validator did not find a problem before search.
        """

        # Build the context object that all feasibility rules use.
        context = FeasibilityContext(
            selected_programs=selected_programs,
            slots=slots,
            config=config,
        )

        # Save all feasibility errors here.
        errors: List[str] = []

        # Run structural rules first.
        # These checks do not need the conflict checkers.
        for rule in self._structural_rules:
            errors.extend(rule.validate(context))

        # Build the same checkers that the scheduler will use.
        checkers = build_checkers(config, courses, selected_programs, slots)

        # Run feasibility bounds from the checkers.
        # These are fast capacity checks for the same rules used during search.
        for checker in checkers:
            errors.extend(checker.feasibility_bound(context))

        return errors