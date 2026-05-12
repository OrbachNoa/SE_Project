"""
conflict_checkers.py
--------------------
IConflictChecker interface and its three concrete implementations:
  - ProgramYearConflictChecker
  - ExcludedDatesChecker
  - ExamPeriodBoundaryChecker
"""
 
from abc import ABC, abstractmethod
from typing import List
 
 
# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------
 
class IConflictChecker(ABC):
    """
    Strategy interface for conflict detection.
 
    Each concrete checker answers a single yes/no question:
    "Does adding `assignment` to the current `schedule` violate a rule?"
 
    Returns True  → conflict detected, assignment must be rejected.
    Returns False → no conflict, assignment is acceptable.
    """
 
    @abstractmethod
    def check(self, assignment, schedule) -> bool:
        """
        Parameters
        ----------
        assignment : ExamAssignment
            The candidate assignment being evaluated.
        schedule : ExamSchedule
            The partial schedule built so far (does NOT yet contain `assignment`).
 
        Returns
        -------
        bool
            True if the assignment passes this checker's rule, False otherwise.
        """
        pass