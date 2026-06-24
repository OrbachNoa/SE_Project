from abc import ABC, abstractmethod
from typing import List


class IConflictChecker(ABC):
    """
    This is the base class for all conflict checkers.

    Every checker must inherit from this class, so the scheduler can use all
    checkers in the same way.

    Each checker can check if a new assignment creates conflict, can prepare
    lookup tables before the search starts, and can do fast feasibility check
    before backtracking.
    """

    @abstractmethod
    def check(self, assignment, schedule) -> bool:
        """
        This function use in the search solution time.

        Checks if putting this assignment inside the schedule breaks the rule
        of this checker.

        Returns True if there is a violation, means reject this assignment.
        Returns False if the assignment is ok.

        This function can be called also for tries that maybe will not really
        be added to the final schedule, so it must not change the checker state.
        """
        pass

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None, selected_index=None) -> None:
        """
        Optional setup before the search starts.

        The default function does nothing.
        Checkers that need to build dicts or cache data can override this.

        The factory calls this function once for every checker, so all checkers
        have the same setup entry point.
        """
        pass

    def feasibility_bound(self, context) -> List[str]:
        """
        Optional fast pre-check before the full search.

        The goal is to catch cases where there is no chance to build valid
        schedule before starting backtracking.

        The default function returns empty list, means this checker didnt find
        any problem.
        """
        return []
