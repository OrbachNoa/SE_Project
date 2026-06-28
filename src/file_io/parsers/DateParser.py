# region Imports
from .FileParser import FileParser
from src.models.Enums import Moed, Semester
from src.models.ExamPeriod import ExamPeriod
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
        lines = self._record_lines(record)
        # Skip records that do not contain the minimum required lines.
        if len(lines) < 2:
            return None

        semester, moed = self._parse_period_header(lines[0])
        start_date, end_date = self._parse_period_range(lines[1])
        excluded_dates = self._parse_excluded_dates(lines[2:])
        return ExamPeriod(semester, moed, start_date, end_date, excluded_dates)

    def _record_lines(self, record):
        """Split a raw period record into meaningful, stripped lines."""
        return [line.strip() for line in record.strip().split('\n') if line.strip()]

    def _parse_period_header(self, line):
        """Parse the '<semester>,<moed>' line."""
        parts = [p.strip() for p in line.split(',')]
        if len(parts) != 2:
            raise ValueError(f"Invalid Exam Period line: {line}")

        semester_str = parts[0].upper()
        moed_str = parts[1].upper()
        try:
            semester = Semester(semester_str)
        except ValueError:
            raise ValueError(f"Invalid semester: '{semester_str}' in line: {line}")

        try:
            moed = Moed(moed_str)
        except ValueError:
            raise ValueError(f"Invalid moed: '{moed_str}' in line: {line}")

        return semester, moed

    def _parse_period_range(self, line):
        """Parse the strict '<start>,<end>' DD-MM-YYYY date range."""
        dates_parts = [p.strip() for p in line.split(',')]
        if len(dates_parts) != 2:
            raise ValueError(f"Invalid Dates line: {line}")
        if not re.match(r"^\d{2}-\d{2}-\d{4}$", dates_parts[0]) or not re.match(r"^\d{2}-\d{2}-\d{4}$", dates_parts[1]):
            raise ValueError(f"Dates must be strictly in DD-MM-YYYY format: {line}")

        try:
            start_date = datetime.strptime(dates_parts[0], "%d-%m-%Y").date()
            end_date = datetime.strptime(dates_parts[1], "%d-%m-%Y").date()
        except ValueError:
            raise ValueError(f"Dates must be valid DD-MM-YYYY format: '{dates_parts[0]}', '{dates_parts[1]}'")
        return start_date, end_date

    def _parse_excluded_dates(self, lines):
        """Parse optional excluded single dates and date ranges."""
        excluded_dates = set()
        for line in lines:
            excluded_dates.update(self._parse_excluded_date_line(line))
        return excluded_dates

    def _parse_excluded_date_line(self, line):
        """Parse one excluded-date line into a set of excluded dates."""
        # Find one-digit or two-digit day and month values, so flexible dates work.
        found_dates = re.findall(r"\d{1,2}-\d{1,2}-\d{4}", line)

        if len(found_dates) == 1:
            return {datetime.strptime(found_dates[0], "%d-%m-%Y").date()}
        if len(found_dates) >= 2:
            d1 = datetime.strptime(found_dates[0], "%d-%m-%Y").date()
            d2 = datetime.strptime(found_dates[1], "%d-%m-%Y").date()
            if d1 > d2:
                raise ValueError(
                    f"Excluded date range is reversed: {found_dates[0]} is after {found_dates[1]}. "
                    f"Range must be written as start, end (earlier date first)."
                )
            excluded = set()
            curr = d1
            while curr <= d2:
                excluded.add(curr)
                curr += timedelta(days=1)
            return excluded

        raise ValueError(f"Invalid excluded date format in line: '{line}'")
