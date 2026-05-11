from typing import List
from src.models.course import Course
from src.models.enums import Moed

class ExamAssignment:
    """
    Represents a specific exam placement for a course.
    """
    def __init__(self, course: Course, date: str, moed: Moed):
        self.course = course
        self.date = date
        self.moed = moed


class ExamSchedule:
    """
    A collection of exam assignments forming a complete schedule.
    """
    def __init__(self):
        # List to store all assignments 
        self.assignments: List[ExamAssignment] = []

    def addAssignment(self, a: ExamAssignment) -> None:
        """
        Adds an assignment to the schedule. 
        """
        pass

    def getByData(self) -> List[ExamAssignment]:
        """
        Returns the list of assignments.
        """
        pass
    
    def removeAssignment(self, a: ExamAssignment) -> None:
        """Removes an assignment from the schedule (for backtracking)."""
        if a in self.assignments:
            self.assignments.remove(a)