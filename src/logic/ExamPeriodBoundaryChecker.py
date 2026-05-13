from src.logic.IConflictChecker import IConflictChecker

class ExamPeriodBoundaryChecker(IConflictChecker):
    """
    This class checks if the exam date is inside the correct start and end dates.
    """
    def __init__(self, periods: list):
        # Save the list of exam periods.
        self._periods = periods

    def check(self, assignment, schedule) -> bool:
        period_found = False
        
        # Step 1: Look at all the periods to find the matching one.
        for p in self._periods:
            if p.moed == assignment.moed and p.semester == assignment.semester:
                period_found = True
                
                # Step 2: Check if the exam date is between the start date and the end date.
                # If the date is smaller than the start date OR bigger than the end date, it is bad.
                if not (p.startDate <= assignment.date <= p.endDate):
                    return True # Return True because it is outside the limits.
        
        # Step 3: If we did not find any matching period for this exam, we return True to be safe.
        if not period_found:
            return True
            
        # Step 4: The date is inside the correct limits. Return False.
        return False