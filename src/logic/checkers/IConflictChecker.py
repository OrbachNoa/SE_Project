from abc import ABC, abstractmethod
from typing import List

class IConflictChecker(ABC):
    """
    This is the base class for all checkers.
    Every checker must use this class.
    """
    @abstractmethod
    def check(self, assignment, schedule) -> bool:
        """
        Checks whether placing `assignment` into `schedule` would violate this
        checker's rule. Returns True if there IS a violation (reject this
        placement), False if the placement is acceptable.

        May be called speculatively, for candidate dates that are never
        actually committed (e.g. during forward-checking domain pruning), so
        implementations must be pure functions of (assignment, schedule) and
        must not mutate checker state here.
        """
        pass

    def prepare(self, courses: list, selected_programs: list = None, slots: list = None) -> None:
        """
        Optional one-time setup before scheduling starts. The default is a
        no-op; checkers that need precomputation override this. The factory
        calls it once per process on every checker, so all checkers share the
        same setup entry point.
        """
        pass

    def feasibility_bound(self, context) -> List[str]:
        """
        Optional preflight check: can this checker's rule possibly be satisfied
        at all, before backtracking starts? The default is a no-op; checkers
        with a closed-form capacity bound override this. context is a
        FeasibilityContext (slots/config/selected programs).
        """
        return []