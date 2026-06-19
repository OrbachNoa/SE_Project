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
    """Assembles the checker list for one scheduling run. Each Phase-3
    threshold checker is added only when its config value is set. Every
    checker's prepare() is then called once, so all precomputation happens in
    this single place inside the worker process.
    """
    min_gap_checkers: List[IConflictChecker] = []
    if config is not None:
        if config.min_gap_obligatory is not None:
            min_gap_checkers.append(MinDaysBetweenExamsChecker(GapScope.OBLIGATORY_ONLY, config.min_gap_obligatory))
        if config.min_gap_any is not None:
            min_gap_checkers.append(MinDaysBetweenExamsChecker(GapScope.ANY, config.min_gap_any))

    checkers: List[IConflictChecker] = [
        ProgramYearConflictChecker(),
        MoedOrderChecker(),
        *min_gap_checkers,
    ]

    if config is not None:
        if config.elective_conflict_cap is not None:
            checkers.append(ElectiveConflictCapChecker(config.elective_conflict_cap))
        if config.exam_span is not None:
            checkers.append(ExamSpanChecker(config.exam_span))
        if config.max_exams_per_day is not None:
            checkers.append(MaxExamsPerDayChecker(config.max_exams_per_day))

    for checker in checkers:
        checker.prepare(courses, selected_programs, slots)
    return checkers