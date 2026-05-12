# ---------------------------------------------------------------------------
# Concrete checker 3 — exam period boundary
# ---------------------------------------------------------------------------

from src.logic.IConflictChecker import IConflictChecker

class ExamPeriodBoundaryChecker(IConflictChecker):
    """
    Ensures the assignment's date lies within [startDate, endDate]
    of its corresponding ExamPeriod (inclusive on both ends).

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

        return not (period.start_date <= assignment.date <= period.end_date)