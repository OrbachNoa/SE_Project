from __future__ import annotations
from typing import List

from src.logic.checkers.IConflictChecker import IConflictChecker
from src.logic.checkers.config.ConstraintRuleDefinitions import (
    BASE_CHECKER_SPECS,
    enabled_checker_specs,
)
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig
from src.logic.indexes.SelectedProgramIndex import SelectedProgramIndex


def build_checkers(config: ConstraintsConfig, courses: list,
                   selected_programs: list = None, slots: list = None,
                   selected_index: SelectedProgramIndex = None) -> List[IConflictChecker]:
    """
    Build the checkers used by one schedule generation run.

    The basic rules are always added.
    Optional rules are added only when the user enabled them in the config.

    prepare() is called here so each checker can build its lookup data once,
    before the scheduler starts checking candidate dates.
    """

    selected_index = selected_index or SelectedProgramIndex(courses, selected_programs, slots)

    # These rules are part of the base scheduler behavior.
    checkers: List[IConflictChecker] = [spec.create(None) for spec in BASE_CHECKER_SPECS]

    # Add the optional rules selected by the user.
    for spec, value in enabled_checker_specs(config):
        checkers.append(spec.create(value))

    # Give every checker the data it needs before the search starts.
    for checker in checkers:
        checker.prepare(courses, selected_programs, slots, selected_index)
        
    return checkers
