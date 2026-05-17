from typing import List, Set, Iterable
from .enums import Semester, Moed
from datetime import timedelta, date

class ExamPeriod:
    """
    Represents the date range for one exam period.
    """
    def __init__(self, semester: Semester, moed: Moed, start_date: date, end_date: date,
                 excluded_dates: Iterable[date]):
        # Reject invalid ranges, so every exam period has a real date window.
        if start_date >= end_date:
            raise ValueError("start date must be strictly less than end date")
        self.semester = semester
        self.moed = moed
        self.startDate = start_date
        self.endDate = end_date
        # Store excluded dates as a set, so date checks stay fast.
        self.excludedDates: Set[date] = set(excluded_dates)

    def getAvailableDates(self) -> List[str]:
        """
        Returns all dates in this period that are not excluded.
        """
        dates = []
        curr = self.startDate
        while curr <= self.endDate:
            if curr not in self.excludedDates:
                dates.append(curr)
            curr += timedelta(days=1)
        return dates
