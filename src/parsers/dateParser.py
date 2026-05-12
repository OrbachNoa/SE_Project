from .fileParser import FileParser
from ..models.enums import Moed, Semester
from ..models.exam_period import ExamPeriod
from datetime import datetime
import re

"""
Parser for exam periods
"""
class ExamPeriodsFileParser(FileParser):

    def parse(self, file_path):
        """
        Parse the file and return the data.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Validate separator
        FileParser.validateSeparator(content)
        
        # Init list to store exam periods
        dates = []
        records = content.split("$$$$")
        # Iterate over all records
        for record in records:
            # If the record is not empty
            if record.strip():
                period = self._parse_date(record)
                # Check if the period is not None
                if period is not None:
                    self._validate_exam_period(period)
                    dates.append(period)
                    
        # Return the list of exam periods
        return dates

    def _validate_exam_period(self, period):
        """
        Validates the exam period.
        """
        # Check if dates are valid strings
        if isinstance(period.startDate, str) or isinstance(period.endDate, str):
            raise ValueError("Dates must be valid DD-MM-YYYY formats.")
            
        # Check that start date is before end date
        if period.startDate > period.endDate:
            raise ValueError(f"Start date is after end date")
        
        # Check that moed is valid
        if period.moed not in Moed:
            raise ValueError(f"Invalid moed: {period.moed}")
            
        # Check that semester is valid
        if period.semester not in Semester:
            raise ValueError(f"Invalid semester: {period.semester}")

    def _parse_date(self, record):
        """
        Parse the exam period.
        """
        # Split the record into lines
        lines = [line.strip() for line in record.strip().split('\n') if line.strip()]
        # Check if there are at least 2 lines
        if len(lines) < 2:
            return None
            
        # Parse Semester and Moed into variables in upper case (e.g., "FALL, Aleph")
        parts = [p.strip() for p in lines[0].split(',')]
        if len(parts) != 2:
            raise ValueError(f"Invalid Exam Period line: {lines[0]}")
            
        semester_str = parts[0].upper()
        moed_str = parts[1].upper()
        # Try to create Semester object from string (will raise ValueError if invalid)
        try:
            semester = Semester(semester_str)
        except ValueError:
            semester = semester_str
            
        # Try to create Moed object from string (will raise ValueError if invalid)
        try:
            moed = Moed(moed_str)
        except ValueError:
            moed = moed_str
            
        # Parse start and end dates into date objects
        dates_parts = [p.strip() for p in lines[1].split(',')]
        if len(dates_parts) != 2:
            raise ValueError(f"Invalid Dates line: {lines[1]}")
            
        try:
            start_date = datetime.strptime(dates_parts[0], "%d-%m-%Y").date()
            end_date = datetime.strptime(dates_parts[1], "%d-%m-%Y").date()
        except ValueError:
            start_date = dates_parts[0]
            end_date = dates_parts[1]
        
        # Add all remaining lines to excluded dates, expanding ranges
        excluded_dates = set()
        from datetime import timedelta
        for i in range(2, len(lines)):
            found_dates = re.findall(r"\d{2}-\d{2}-\d{4}", lines[i])
            if len(found_dates) == 1:
                d = datetime.strptime(found_dates[0], "%d-%m-%Y").date()
                excluded_dates.add(d)
            elif len(found_dates) >= 2:
                # Handle range
                d1 = datetime.strptime(found_dates[0], "%d-%m-%Y").date()
                d2 = datetime.strptime(found_dates[1], "%d-%m-%Y").date()
                curr = d1
                while curr <= d2:
                    excluded_dates.add(curr)
                    curr += timedelta(days=1)
            
        # Return the exam period
        return ExamPeriod(semester, moed, start_date, end_date, list(excluded_dates))