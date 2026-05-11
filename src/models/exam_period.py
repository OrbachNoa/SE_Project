from typing import List
from src.models.enums import Semester, Moed

class ExamPeriod:
    """
    Represents the timeframe for an exam session.
    """
    def __init__(self, semester: Semester, moed: Moed, start_date: str, end_date: str, excluded_dates: List[str]):
        self.semester = semester
        self.moed = moed
        self.startDate = start_date
        self.endDate = end_date
        self.excludedDates = excluded_dates

    def getAvailableDates(self) -> List[str]:
        """
        Calculates and returns the list of dates available for exams.
        To be implemented.
        """
        pass