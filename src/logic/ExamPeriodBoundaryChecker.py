from .IConflictChecker import IConflictChecker

class ExamPeriodBoundaryChecker(IConflictChecker):
    """
    Checks that each exam date stays inside its exam period.
    """
    def __init__(self, periods: list):
        # Store the exam periods, so each assignment can be checked against them.
        self._periods = periods

    def check(self, assignment, schedule) -> bool:
        # Find periods with the same semester and moed, so we check the right window.
        matching_periods = [
            p for p in self._periods
            if p.moed == assignment.moed and p.semester == assignment.semester
        ]

        # Treat a missing period as a conflict, so invalid assignments are rejected.
        if not matching_periods:
            return True

        # Accept the date if it fits inside one matching period.
        for p in matching_periods:
            if p.startDate <= assignment.date <= p.endDate:
                return False  # The date is inside this period, so there is no conflict.

        # Reject the date if no matching period contains it.
        return True
