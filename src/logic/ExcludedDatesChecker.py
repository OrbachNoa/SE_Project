# ---------------------------------------------------------------------------
# Concrete checker 2 — excluded dates
# ---------------------------------------------------------------------------
 
from src.logic.IConflictChecker import IConflictChecker

class ExcludedDatesChecker(IConflictChecker):
    """
    Ensures the assignment's date does not fall on an excluded date
    (Shabbat, holiday, etc.) within its corresponding ExamPeriod.
 
    The relevant ExamPeriod is identified by matching both
    `semester` and `moed` with those stored on the assignment.
 
    If no matching period is found the assignment is rejected (fail-safe).
    """
 
    def __init__(self, periods: list):
        """
        Parameters
        ----------
        periods : List[ExamPeriod]
            All exam periods loaded from the periods file.
        """
        self._periods = periods
 
    def _findPeriod(self, assignment):
        """Return the ExamPeriod that matches the assignment's semester+moed, or None."""
        for period in self._periods:
            if period.semester == assignment.semester and period.moed == assignment.moed:
                return period
        return None
 
    def check(self, assignment, schedule) -> bool:
        period = self._findPeriod(assignment)
 
        if period is None:
            return True   # no period found → conflict detected → reject
 
        return assignment.date in period.excluded_dates