# region Imports
from .fileParser import FileParser
from ..models.enums import EvalType, Semester, Requirement
from ..models.course import Course, ProgramEntry
# endregion

class CoursesFileParser(FileParser):
    """Parses course records into course objects."""
    def parse(self, file_path):
        """Reads the course file and returns course objects."""
        # Open the file and read its content.
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Validate the separator, so badly formatted multi-record files are caught.
        try:
            FileParser.validateSeparator(content)
        except ValueError:
            pass

        # Initialize the list of courses.
        courses = []
        # Track parsed courses and IDs, so duplicate course IDs can be rejected.
        seen_ids = set()

        # Split the content into records based on the separator.
        records = content.split("$$$$")
        # Parse each non-empty record, so blank sections are ignored.
        for record in records:
            if record.strip():
                # Parse the record.
                course = self._parse_course(record)
                if course is not None:
                    # Validate each course before adding it to the result.
                    self._validate_course(course)
                    # Reject duplicate IDs, so each course appears only once.
                    if course.courseId in seen_ids:
                        raise ValueError(f"Duplicate course ID found: {course.courseId}")
                    # Add the course to the result if it's not a duplicate.
                    seen_ids.add(course.courseId)
                    # Add the valid course, so it can be scheduled later.
                    courses.append(course)
        # Return all valid courses found in the file.
        return courses

    def _validate_course(self, course):
        """Checks that a parsed course has valid field values."""
        # Validate the evaluation type, so only known options are accepted.
        if course.evaluation not in EvalType:
            raise ValueError(f"Invalid evaluation: {course.evaluation}")

        # Validate the course ID, so it matches the expected five-digit format.
        if len(course.courseId) != 5 or not course.courseId.isdigit():
            raise ValueError(f"Invalid course ID: {course.courseId}")

        # Require at least one program entry, so the course belongs to a program.
        if not course.programEntries:
            raise ValueError(f"Course '{course.courseId}' has no program entries.")

        # Track program-year pairs, so duplicate entries inside one course are rejected.
        seen_entries = set()

        # Validate each program entry, so bad course data is rejected early.
        for entry in course.programEntries:
            # Build a program-year key, so the same pair cannot appear twice.
            key = (entry.programId, entry.year)
            if key in seen_entries:
                raise ValueError(f"Duplicate program entry found for course '{course.courseId}': Program {entry.programId}, Year {entry.year}")
            seen_entries.add(key)

    def _parse_course(self, record: str) -> Course:
        """Converts one text record into a Course object."""
        # Split the record into clean lines, so empty lines do not affect parsing.
        lines = [line.strip() for line in record.strip().split('\n') if line.strip()]
        # Require the basic fields, so incomplete course records are rejected.
        if len(lines) < 4:
            raise ValueError(f"Course record is too short (must have at least 4 lines): {lines}")

        # Read the course name from the first line.
        name = lines[0]
        # Read the course ID from the second line.
        course_id = lines[1]
        # Read the instructor name from the third line.
        instructor = lines[2]
        # Read the evaluation type from the last line.
        evaluation_str = lines[-1].upper()
        try:
            evaluation = EvalType(evaluation_str)
        except ValueError:
            raise ValueError(f"Invalid evaluation type: '{evaluation_str}'")

        # Initialize the list of program entries.
        program_entries = []

        # Parse each middle line as one program entry.
        for i in range(3, len(lines) - 1):
            parts = [p.strip() for p in lines[i].split(',')]
            # Require four fields, so each program entry has all needed data.
            if len(parts) == 4:
                # Read the program ID from the first field.
                program_id = parts[0].strip()
                # Read and validate the study year from the second field.
                year_str = parts[1].strip()
                if not year_str.isdigit():
                    raise ValueError(f"Year must be a digit, got: '{year_str}' in line: {lines[i]}")
                year = int(year_str)
                # Read the semester, so bad values fail before scheduling.
                semester_str = parts[2].upper()
                try:
                    semester = Semester(semester_str)
                except ValueError:
                    raise ValueError(f"Invalid semester '{semester_str}' in line: {lines[i]}")
                # Read the requirement, so bad values fail before scheduling.
                req_str = parts[3].upper()
                try:
                    requirement = Requirement(req_str)
                except ValueError:
                    raise ValueError(f"Invalid requirement '{req_str}' in line: {lines[i]}")
                # Create a program entry, so it can be stored on the course.
                entry = ProgramEntry(program_id, year, semester, requirement)
                # Add the program entry to the list.
                program_entries.append(entry)
            else:
                raise ValueError(f"Invalid program entry format: {lines[i]}")

        # Return the parsed course object.
        return Course(course_id, name, instructor, evaluation, program_entries)
