from abc import ABC, abstractmethod

class IConflictChecker(ABC):
    """
    This is the base class for all checkers.
    Every checker must use this class.
    """
    @abstractmethod
    def check(self, assignment, schedule) -> bool:
        """
        This function checks if we can add a new exam to the schedule.
        Step 1: It takes the new exam (assignment).
        Step 2: It takes the current schedule.
        Step 3: It returns True if there is a problem (a conflict).
        Step 4: It returns False if everything is okay and safe.
        """
        pass