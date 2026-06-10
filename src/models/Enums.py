from enum import Enum

class EvalType(Enum):
    """
    Defines how a course is evaluated. 
    """
    EXAM = "EXAM"
    PROJECT = "PROJECT"
    ATTENDANCE = "ATTENDANCE"

class Semester(Enum):
    """
    Academic semesters available in the system.
    Used for filtering and sorting (FALL, SPRING, SUMMER).
    """
    FALL = "FALL"
    SPRI = "SPRI"
    SUMM = "SUMM"

class Moed(Enum):
    """
    Exam sessions (Moedim). 
    Used for scheduling and output grouping.
    """
    ALEPH = "ALEPH"
    BET = "BET"
    GIMEL = "GIMEL"

class Requirement(Enum):
    """
    Course status within a specific program.
    OBLIGATORY counts for +2 in the difficulty score.
    """
    OBLIGATORY = "OBLIGATORY"
    ELECTIVE = "ELECTIVE"