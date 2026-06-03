from typing import List
from src.models.Enums import EvalType, Semester, Requirement

class ProgramEntry:
    """
    Represents a specific program requirement.
    """
    def __init__(self, program_id: str, year: int, semester: Semester, requirement: Requirement):
        # Added checks for 'year' and 'program_id' to prevent creating an invalid object.
        if year not in [1, 2, 3, 4]:
            raise ValueError(f"Invalid year: {year}")
        if not isinstance(program_id, str):
            raise TypeError(f"programId must be str, got {type(program_id).__name__}")
        if len(program_id) != 5 or not program_id.isdigit():
            raise ValueError(f"Invalid program ID: {program_id}")
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