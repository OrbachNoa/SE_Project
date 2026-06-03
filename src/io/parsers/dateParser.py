# region Imports
from .FileParser import FileParser
from ...models.Enums import Moed, Semester
from ...models.ExamPeriod import ExamPeriod
from datetime import datetime, timedelta
import re
# endregion

class ExamPeriodsFileParser(FileParser):
    """Parses exam-period records into ExamPeriod objects."""

    def parse(self, file_path):
        """Reads the exam-period file and returns exam periods."""
        # Open the file and read its content.
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Validate the separator, so badly formatted multi-record files are caught.
        try:
            FileParser.validateSeparator(content, separator="$$$$")
        except ValueError:
            lines = [line for line in content.split('\n') if line.strip()]
            if len(lines) > 5:
                raise ValueError("Exam periods file is missing the '$$$$' separator between records.")

        # Initialize the list of exam periods.
        dates = []
        # Track parsed periods and keys, so duplicates can be rejected.
        seen_combos = set()
        # Split the content into records based on the separator.
        records = content.split("$$$$")

        # Parse each non-empty record, so blank sections are ignored.
        for record in records:
            if record.strip():
                # Parse the record.
                period = self._parse_date(record)
                if period is not None:
                    # Reject duplicate semester-moed combos, so each appears once.
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

    def _parse_date(self, record):
        """Converts one text record into an ExamPeriod object."""
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
        # Parse the semester, so unknown values fail early.
        try:
            semester = Semester(semester_str)
        except ValueError:
            raise ValueError(f"Invalid semester: '{semester_str}' in line: {lines[0]}")

        # Parse the moed, so unknown values fail early.
        try:
            moed = Moed(moed_str)
        except ValueError:
            raise ValueError(f"Invalid moed: '{moed_str}' in line: {lines[0]}")

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
            raise ValueError(f"Dates must be valid DD-MM-YYYY format: '{dates_parts[0]}', '{dates_parts[1]}'")

        # Collect excluded dates, so unavailable days are not used for exams.
        excluded_dates = set()

        for i in range(2, len(lines)):
            # Find one-digit or two-digit day and month values, so flexible dates work.
            found_dates = re.findall(r"\d{1,2}-\d{1,2}-\d{4}", lines[i])

            if len(found_dates) == 1:
                d = datetime.strptime(found_dates[0], "%d-%m-%Y").date()
                excluded_dates.add(d)
            elif len(found_dates) >= 2:
                # Expand the range, so every date in it is excluded.
                d1 = datetime.strptime(found_dates[0], "%d-%m-%Y").date()
                d2 = datetime.strptime(found_dates[1], "%d-%m-%Y").date()
                if d1 > d2:
                    # Reject reversed ranges, so input order stays clear.
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

        # Build the ExamPeriod, so its constructor can validate the range.
        return ExamPeriod(semester, moed, start_date, end_date, excluded_dates)
