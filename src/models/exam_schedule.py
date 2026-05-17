from typing import List
from .course import Course
from .enums import Moed, Semester

class ExamAssignment:
    """
    Represents a specific exam placement for a course.
    """
    def __init__(self, course: Course, date: str, moed: Moed, semester: Semester):
        self.course = course
        self.date = date
        self.moed = moed
        self.semester = semester

# Holds all exam assignments that make one complete schedule.
class ExamSchedule:
    def __init__(self):
        # Store assignments in the order they were added.
        self.assignments: List[ExamAssignment] = []
        # Index courses by date, so conflict checks can avoid scanning every assignment.
        self._date_to_course_ids: dict = {}

    # Add an assignment and update the date index.
    def addAssignment(self, a: ExamAssignment) -> None:
        # Block duplicate moeds, so the same course is not scheduled twice.
        for existing in self.assignments:
            if existing.course.courseId == a.course.courseId and existing.moed == a.moed:
                raise ValueError(f"Logical Error: Course {a.course.courseId} already scheduled for {a.moed.name}")

        # Store the assignment, so it becomes part of the schedule.
        self.assignments.append(a)
        if a.date not in self._date_to_course_ids:
            self._date_to_course_ids[a.date] = set()
        self._date_to_course_ids[a.date].add(a.course.courseId)

    # Return assignments on the requested date.
    def getByDate(self, target_date) -> List[ExamAssignment]:
        return [a for a in self.assignments if a.date == target_date]

    # Remove the latest assignment, so backtracking can try another option.
    def removeAssignment(self, a: ExamAssignment = None) -> None:
        if not self.assignments:
            return
        removed = self.assignments.pop()
        date_set = self._date_to_course_ids.get(removed.date)
        if date_set:
            date_set.discard(removed.course.courseId)
