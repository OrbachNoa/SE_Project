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
        """
        pass