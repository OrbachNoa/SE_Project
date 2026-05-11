from typing import List
from src.models.enums import EvalType, Semester, Requirement

class ProgramEntry:
    """
    Represents a specific program requirement.
    """
    def __init__(self, program_id: int, year: int, semester: Semester, requirement: Requirement):
        self.programId = program_id
        self.year = year
        self.semester = semester
        self.requirement = requirement


class Course:
    """
    Represents a course in the academic system.
    """
    def __init__(self, course_id: str, name: str, instructor: str, evaluation: EvalType, program_entries: List[ProgramEntry]):
        self.courseId = course_id
        self.name = name
        self.instructor = instructor
        self.evaluation = evaluation
        self.programEntries = program_entries

    def hasExam(self) -> bool:
        """Checks if the course evaluation is an EXAM."""
        return self.evaluation == EvalType.EXAM