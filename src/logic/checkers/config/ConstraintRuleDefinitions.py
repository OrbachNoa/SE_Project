from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from src.logic.checkers.ElectiveConflictCapChecker import ElectiveConflictCapChecker
from src.logic.checkers.ExamSpanChecker import ExamSpanChecker
from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.checkers.MaxExamsPerDayChecker import MaxExamsPerDayChecker
from src.logic.checkers.MinDaysBetweenExamsChecker import GapScope, MinDaysBetweenExamsChecker
from src.logic.checkers.MoedOrderChecker import MoedOrderChecker
from src.logic.checkers.ProgramYearConflictChecker import ProgramYearConflictChecker


@dataclass(frozen=True)
class CheckerSpec:
    """Small factory definition for one checker."""

    field_name: Optional[str]
    create: Callable[[object], IConflictChecker]


BASE_CHECKER_SPECS = (
    CheckerSpec(None, lambda value: ProgramYearConflictChecker()),
    CheckerSpec(None, lambda value: MoedOrderChecker()),
)

OPTIONAL_CHECKER_SPECS = (
    CheckerSpec(
        "min_gap_obligatory",
        lambda value: MinDaysBetweenExamsChecker(GapScope.OBLIGATORY_ONLY, value),
    ),
    CheckerSpec(
        "min_gap_any",
        lambda value: MinDaysBetweenExamsChecker(GapScope.ANY, value),
    ),
    CheckerSpec(
        "elective_conflict_cap",
        lambda value: ElectiveConflictCapChecker(value),
    ),
    CheckerSpec(
        "exam_span",
        lambda value: ExamSpanChecker(value),
    ),
    CheckerSpec(
        "max_exams_per_day",
        lambda value: MaxExamsPerDayChecker(value),
    ),
)


def enabled_checker_specs(config) -> List[tuple[CheckerSpec, object]]:
    """Return optional checker specs that are enabled in the config."""

    if config is None:
        return []

    enabled = []
    for spec in OPTIONAL_CHECKER_SPECS:
        value = getattr(config, spec.field_name)
        if value is not None:
            enabled.append((spec, value))
    return enabled


def mandatory_gap_value(config) -> Optional[int]:
    """Return the strictest mandatory gap enabled by the config."""

    if config is None:
        return None

    gaps = [
        value for value in (config.min_gap_obligatory, config.min_gap_any)
        if value is not None
    ]
    return max(gaps) if gaps else None
