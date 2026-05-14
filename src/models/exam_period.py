from typing import List
from src.models.enums import Semester, Moed
from datetime import timedelta, date

class ExamPeriod:
    """
    Represents the timeframe for an exam session.
    """
    def __init__(self, semester: Semester, moed: Moed, start_date: date, end_date: date, excluded_dates: List[date]):
        # Added a check for 'start_date' and 'end_date' to prevent creating an invalid object.
        if start_date >= end_date:
            raise ValueError("start date must be strictly less than end date")
        self.semester = semester
        self.moed = moed
        self.startDate = start_date
        self.endDate = end_date
        self.excludedDates = excluded_dates

    def getAvailableDates(self) -> List[str]:
        """
        Calculates and returns the list of dates available for exams.
        """
        dates = []
        curr = self.startDate
        while curr <= self.endDate:
            if curr not in self.excludedDates:
                dates.append(curr)
            curr += timedelta(days=1)
        return dates