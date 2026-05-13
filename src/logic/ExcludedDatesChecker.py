from src.logic.IConflictChecker import IConflictChecker

class ExcludedDatesChecker(IConflictChecker):
    """
    This class checks if the exam date is on a day we are not allowed to use.
    For example, we cannot use holidays or weekends.
    """
    def __init__(self, periods: list):
        # Save the list of exam periods when we create this object.
        self._periods = periods

    def check(self, assignment, schedule) -> bool:
        # Look at all the periods we have.
        for p in self._periods:
            
            # Find the period that matches the semester and moed of our new exam.
            if p.moed == assignment.moed and p.semester == assignment.semester:
                
                # Check if the new exam date is inside the 'excludedDates' list.
                if assignment.date in p.excludedDates:
                    # The date is not allowed. Return True (this is a conflict).
                    return True
                    
        # The date is allowed. Return False (no conflict).
        return False