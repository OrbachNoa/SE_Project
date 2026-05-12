from .fileParser import FileParser
from ..models.enums import Moed, Semester
from ..models.exam_period import ExamPeriod
from datetime import datetime
import re

"""
Parser for exam periods
"""
class DateParser(FileParser):

    def parse(self, file_path):
        """
        Parse the file and return the data.
        """
        # Init list to store exam periods
        dates = []
        
        # Open the file and parse it
        with open(file_path, "r", encoding="utf-8") as file:
            current_record = []
            # Go through each line in the file
            for line in file:
                # Check if the line is a separator
                if self._validate_separator(line):
                    # If the line is a separator and there is a current record, parse it
                    if current_record:
                        period = self._parse_date("\n".join(current_record))
                        if period is not None:
                            self._validate_exam_period(period)
                            dates.append(period)
                        current_record = []
                # Otherwise, add the line to the current record
                else:
                    if line.strip():
                        current_record.append(line.strip())
            
            # Process the very last record
            if current_record:
                period = self._parse_date("\n".join(current_record))
                if period is not None:
                    self._validate_exam_period(period)
                    dates.append(period)
        
        # Return the list of exam periods
        return dates

    def _validate_exam_period(self, period):
        """
        Validates the exam period.
        """
        # check that the periods are rightly formatted DD-MM-YYYY
        try:
            start_date = datetime.strptime(period.startDate, "%d-%m-%Y")
        except ValueError:
            raise ValueError(f"Invalid start date format: {period.startDate}")
        try:
            end_date = datetime.strptime(period.endDate, "%d-%m-%Y")
        except ValueError:
            raise ValueError(f"Invalid end date format: {period.endDate}")
        
        # check that start date is before end date
        if start_date > end_date:
            raise ValueError(f"Start date is after end date")
        
        # check that moed is valid
        if period.moed not in Moed:
            raise ValueError(f"Invalid moed: {period.moed}")
        
        # check that semester is valid
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
            
        # Parse start and end dates into variables in the format "29-01-2026"
        dates_parts = [p.strip() for p in lines[1].split(',')]
        if len(dates_parts) != 2:
            raise ValueError(f"Invalid Dates line: {lines[1]}")
            
        start_date = dates_parts[0]
        end_date = dates_parts[1]
        
        # Add all remaining lines to excluded dates
        excluded_dates = []
        for i in range(2, len(lines)):
            # Extract only the dates (DD-MM-YYYY) and ignore the text reasons
            found_dates = re.findall(r"\d{2}-\d{2}-\d{4}", lines[i])
            excluded_dates.extend(found_dates)
            
        # Return the exam period
        return ExamPeriod(semester, moed, start_date, end_date, excluded_dates)