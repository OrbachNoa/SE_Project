from .fileParser import FileParser
from ..models.enums import Moed, Semester
from ..models.exam_period import ExamPeriod
from datetime import datetime
import re

"""
Parses exam-period records into ExamPeriod objects.
"""
class ExamPeriodsFileParser(FileParser):

    def parse(self, file_path):
        """
        Reads the exam-period file and returns exam periods.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Validate the separator, so badly formatted multi-record files are caught.
        try:
            FileParser.validateSeparator(content)
        except ValueError:
            pass

        # Track parsed periods and keys, so duplicates can be rejected.
        dates = []
        seen_combos = set()
        records = content.split("$$$$")
        # Parse each non-empty record, so blank sections are ignored.
        for record in records:
            if record.strip():
                period = self._parse_date(record)
                if period is not None:
                    # Validate each period before adding it to the result.
                    self._validate_exam_period(period)
                    combo = (period.semester, period.moed)
                    if combo in seen_combos:
                        raise ValueError(
                            f"Duplicate exam period for "
                            f"{period.semester.name}, {period.moed.name}. "
                            f"Each (semester, moed) must appear at most once."
                        )
                    seen_combos.add(combo)
                    dates.append(period)

        # Return all valid exam periods found in the file.
        return dates

    def _validate_exam_period(self, period):
        """
        Checks that a parsed exam period has valid field values.
        """
        # Reject raw date strings, so only parsed date objects are accepted.
        if isinstance(period.startDate, str) or isinstance(period.endDate, str):
            raise ValueError("Dates must be valid DD-MM-YYYY formats.")

        # Require the start date to be before the end date.
        if period.startDate >= period.endDate:
            raise ValueError(f"Start date must be strictly before end date")

        # Validate the moed, so only known moed values are accepted.
        if period.moed not in Moed:
            raise ValueError(f"Invalid moed: {period.moed}")

        # Validate the semester, so only known semester values are accepted.
        if period.semester not in Semester:
            raise ValueError(f"Invalid semester: {period.semester}")

    def _parse_date(self, record):
        """
        Converts one text record into an ExamPeriod object.
        """
        # Split the record into clean lines, so empty lines do not affect parsing.
        lines = [line.strip() for line in record.strip().split('\n') if line.strip()]
        # Skip records that do not contain the minimum required lines.
        if len(lines) < 2:
            return None

        # Split semester and moed, so each field can be parsed separately.
        parts = [p.strip() for p in lines[0].split(',')]
        if len(parts) != 2:
            raise ValueError(f"Invalid Exam Period line: {lines[0]}")

        semester_str = parts[0].upper()
        moed_str = parts[1].upper()
        # Parse the semester value, so valid strings become enum values.
        try:
            semester = Semester(semester_str)
        except ValueError:
            semester = semester_str

        # Parse the moed value, so valid strings become enum values.
        try:
            moed = Moed(moed_str)
        except ValueError:
            moed = moed_str

        # Split the start and end dates, so each date can be parsed.
        dates_parts = [p.strip() for p in lines[1].split(',')]
        if len(dates_parts) != 2:
            raise ValueError(f"Invalid Dates line: {lines[1]}")
        if not re.match(r"^\d{2}-\d{2}-\d{4}$", dates_parts[0]) or not re.match(r"^\d{2}-\d{2}-\d{4}$", dates_parts[1]):
            raise ValueError(f"Dates must be strictly in DD-MM-YYYY format: {lines[1]}")

        try:
            start_date = datetime.strptime(dates_parts[0], "%d-%m-%Y").date()
            end_date = datetime.strptime(dates_parts[1], "%d-%m-%Y").date()
        except ValueError:
            start_date = dates_parts[0]
            end_date = dates_parts[1]

        # Collect excluded dates, so unavailable days are not used for exams.
        excluded_dates = set()
        from datetime import timedelta
        for i in range(2, len(lines)):
            # Find one-digit or two-digit day and month values, so flexible dates work.
            found_dates = re.findall(r"\d{1,2}-\d{1,2}-\d{4}", lines[i])

            if len(found_dates) == 1:
                d = datetime.strptime(found_dates[0], "%d-%m-%Y").date()
                excluded_dates.add(d)
            elif len(found_dates) >= 2:
                # Expand a date range, so every date in the range is excluded.
                d1 = datetime.strptime(found_dates[0], "%d-%m-%Y").date()
                d2 = datetime.strptime(found_dates[1], "%d-%m-%Y").date()
                if d1 > d2:
                    raise ValueError(
                        f"Excluded date range is reversed: {found_dates[0]} is after {found_dates[1]}. "
                        f"Range must be written as start, end (earlier date first)."
                    )
                curr = d1
                while curr <= d2:
                    excluded_dates.add(curr)
                    curr += timedelta(days=1)
            else:
                # Reject unclear excluded-date lines, so invalid input fails loudly.
                raise ValueError(f"Invalid excluded date format in line: '{lines[i]}'")

        # Return the exam period with its excluded dates.
        return ExamPeriod(semester, moed, start_date, end_date, excluded_dates)