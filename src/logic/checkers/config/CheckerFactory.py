from __future__ import annotations
from typing import List

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.checkers.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.checkers.MoedOrderChecker import MoedOrderChecker
from src.logic.checkers.MinDaysBetweenExamsChecker import MinDaysBetweenExamsChecker, GapScope
from src.logic.checkers.ElectiveConflictCapChecker import ElectiveConflictCapChecker
from src.logic.checkers.ExamSpanChecker import ExamSpanChecker
from src.logic.checkers.MaxExamsPerDayChecker import MaxExamsPerDayChecker
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig


def build_checkers(config: ConstraintsConfig, courses: list,
                   selected_programs: list = None, slots: list = None) -> List[IConflictChecker]:
    """
    Build the checkers used by one schedule generation run.

    The basic rules are always added.
    Optional rules are added only when the user enabled them in the config.

    prepare() is called here so each checker can build its lookup data once,
    before the scheduler starts checking candidate dates.
    """

    # Add the minimum-gap rules only if the user turned them on.
    min_gap_checkers: List[IConflictChecker] = []
    if config is not None:
        if config.min_gap_obligatory is not None:
            min_gap_checkers.append(MinDaysBetweenExamsChecker(GapScope.OBLIGATORY_ONLY, config.min_gap_obligatory))
        if config.min_gap_any is not None:
            min_gap_checkers.append(MinDaysBetweenExamsChecker(GapScope.ANY, config.min_gap_any))

    # These rules are part of the base scheduler behavior.
    checkers: List[IConflictChecker] = [
        ProgramYearConflictChecker(),
        MoedOrderChecker(),
        *min_gap_checkers,
    ]

    # Add the rest of the optional rules selected by the user.
    if config is not None:
        if config.elective_conflict_cap is not None:
            checkers.append(ElectiveConflictCapChecker(config.elective_conflict_cap))

        if config.exam_span is not None:
            checkers.append(ExamSpanChecker(config.exam_span))

        if config.max_exams_per_day is not None:
            checkers.append(MaxExamsPerDayChecker(config.max_exams_per_day))

    # Give every checker the data it needs before the search starts.
    for checker in checkers:
        checker.prepare(courses, selected_programs, slots)
        
    return checkers