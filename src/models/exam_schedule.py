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

# A collection of exam assignments forming a complete schedule.
class ExamSchedule:
    def __init__(self):
        # List to store all assignments 
        self.assignments: List[ExamAssignment] = []

    # Adds an assignment to the schedule.
    def addAssignment(self, a: ExamAssignment) -> None:
        self.assignments.append(a)

    # Returns the list of assignments.
    def getByData(self, target_date) -> List[ExamAssignment]:
        return [a for a in self.assignments if a.date == target_date]
    
    # Removes an assignment from the schedule (for backtracking).
    def removeAssignment(self, a: ExamAssignment) -> None:
        if a in self.assignments:
            self.assignments.remove(a)