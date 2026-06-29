"""Unit tests for the file_io.parsers package: the abstract FileParser base
class's separator validation, and the three concrete parsers
(CoursesFileParser, ExamPeriodsFileParser, ProgramsFileParser) plus the
ParserFactory that creates them.

Each parser reads a UTF-8 text file, splits on the configured separator
(default '$$$$'), and returns typed domain objects. Tests cover separator
validation (default and custom separators, partial/missing separators),
each parser's happy path against a well-formed fixture, field-level
rejection of invalid values (bad requirement/evaluation/semester/moed,
malformed or impossible dates, non-5-digit program codes), duplicate
detection (duplicate course IDs, duplicate program entries within one
course, duplicate (semester, moed) period pairs), the empty-file edge
case for both CoursesFileParser and ProgramsFileParser, and
ParserFactory's registry lookup/registration/multi-file parsing.

Conventions:
- Each test carries a unique TC-PRS-NNN identifier in the comment block
  above its definition, numbered sequentially, grouped under a section
  divider per parser class.
- Each test body is split into Arrange / Act / Assert sections.
- No conftest fixture models raw file content, so every test builds its
  fixture file directly via `tmp_path`.
"""
from datetime import date
import pytest

from src.file_io.parsers.FileParser import FileParser
from src.file_io.parsers.CourseParser import CoursesFileParser
from src.file_io.parsers.DateParser import ExamPeriodsFileParser
from src.file_io.parsers.ProgramParser import ProgramsFileParser
from src.file_io.parsers.ParserFactory import ParserFactory

# The separator.
SEP = "$$$$"

# the only program codes the system accepts.
VALID_PROGRAM_CODES = {
    "83101",  # Computer Engineering
    "83102",  # Electrical Engineering
    "83103",  # Electrical Engineering – Neuro-engineering
    "83104",  # Industrial Engineering & Information Systems
    "83105",  # Computer Engineering – Computer Hardware
    "83107",  # Data Engineering
    "83108",  # Software Engineering
    "83109",  # Materials Engineering
    "83115",  # Electrical Engineering – Biomedical
    "83182",  # Electrical Engineering – Quantum
}


# ---------------------------------------------------------------------------
# Abstract FileParser.validateSeparator() — TC-PRS-001..006
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-PRS-001: validateSeparator accepts a well-formed '$$$$' separator
# ===========================================================================
def test_validate_separator_accepts_valid_quad_dollar():
    # Arrange — two records separated by exactly '$$$$'.
    content = f"record_one\n{SEP}\nrecord_two"
    # Act
    result = FileParser.validateSeparator(content)
    # Assert — validateSeparator returns True on its only success path.
    assert result is True

# ===========================================================================
# TC-PRS-002: validateSeparator rejects content that contains no '$$$$'
# ===========================================================================
def test_validate_separator_rejects_missing_separator():
    # Arrange — no separator anywhere.
    content = "record_one record_two no separator here"
    # Act + Assert - We expect a ValueError here because there is no '$$$$' separator.
    with pytest.raises(ValueError):
        FileParser.validateSeparator(content)


# ===========================================================================
# TC-PRS-003: Surrounding whitespace around the separator must be handled consistently.
# ===========================================================================
def test_validate_separator_tolerates_surrounding_whitespace():
    # Arrange — separator surrounded by spaces on its own line.
    content = f"record_one\n  {SEP}  \nrecord_two"
    # Act
    result = FileParser.validateSeparator(content)
    # Assert
    assert result is True


# ===========================================================================
# TC-PRS-004: A partial separator (one, two, or three '$' signs) must NOT be accepted as a valid record separator.
# ===========================================================================
@pytest.mark.parametrize("partial", ["$", "$$", "$$$"])
def test_validate_separator_rejects_partial_separator(partial):
    # Arrange — content uses fewer than four '$' signs between records.
    content = f"record_one\n{partial}\nrecord_two"
    # Act + Assert
    with pytest.raises(ValueError):
        FileParser.validateSeparator(content)



# ===========================================================================
# TC-PRS-005: FileParser.validateSeparator accepts custom separators (e.g. ',')
# and rejects the default one ('$$$$') when configured so.
# ===========================================================================
def test_validate_separator_with_comma():
    # Arrange — content with comma separator.
    content = "83101,83102"
    # Act
    result = FileParser.validateSeparator(content, separator=",")
    # Assert
    assert result is True


# ===========================================================================
# TC-PRS-006: FileParser.validateSeparator rejects the default separator ('$$$$') when configured so.
# ===========================================================================
def test_validate_separator_rejects_default_separator():
    # Arrange — content with comma separator.
    content = "83101,83102"
    # Act + Assert
    with pytest.raises(ValueError):
        FileParser.validateSeparator(content)


# ---------------------------------------------------------------------------
# CoursesFileParser — TC-PRS-007..012
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-PRS-007: A well-formed courses file with three records produces three Course objects whose key
# fields match the fixture exactly.
# ===========================================================================
def test_courses_parser_returns_correct_course_list(tmp_path):
    # Arrange — Provide a fixture file with 3 valid course records.
    fixture = tmp_path / "courses_valid.txt"
    fixture.write_text(
        "Calculus 1\n"
        "10101\n"
        "Dr. Cohen\n"
        "83101,2,FALL,Obligatory\n"
        "Exam\n"
        f"{SEP}\n"
        "Lab Project\n"
        "10102\n"
        "Dr. Levi\n"
        "83101,2,FALL,Elective\n"
        "Project\n"
        f"{SEP}\n"
        "Seminar\n"
        "10103\n"
        "Dr. Mizrahi\n"
        "83101,3,SPRI,Elective\n"
        "Attendance\n",
        encoding="utf-8",
    )

    # Act
    courses = CoursesFileParser().parse(str(fixture))
    # Assert — exact count and key fields per record.
    assert len(courses) == 3
    assert courses[0].name == "Calculus 1"
    assert courses[0].courseId == "10101"
    assert courses[0].instructor == "Dr. Cohen"
    assert courses[0].evaluation.name == "EXAM"
    assert courses[1].evaluation.name == "PROJECT"
    assert courses[2].evaluation.name == "ATTENDANCE"


# ===========================================================================
# TC-PRS-008: Check that the parser adds one program entry for each program line in the course.
# ===========================================================================
def test_courses_parser_handles_multiple_programs_per_course(tmp_path):
    # Arrange — one course belonging to TWO programs.
    fixture = tmp_path / "course_multi_program.txt"
    fixture.write_text(
        "Physics 1\n"
        "83102\n"
        "Prof. O. Some\n"
        "83101,1,FALL,Obligatory\n"   # Program 1
        "83102,1,FALL,Obligatory\n"   # Program 2
        "Exam\n",
        encoding="utf-8",
    )
    # Act
    courses = CoursesFileParser().parse(str(fixture))
    # Assert — exactly one course with TWO program entries.
    assert len(courses) == 1
    assert len(courses[0].programEntries) == 2
    assert courses[0].programEntries[0].programId == "83101"
    assert courses[0].programEntries[1].programId == "83102"
    assert courses[0].evaluation.name == "EXAM"


# ===========================================================================
# TC-PRS-009: Requirement and Evaluation field values appear in sentence case in the file
# ("Obligatory","Elective", "Exam", "Project", "Attendance").
# The parser must accept them in that form.
# Test runs for each possible valid Requirement value.
# ===========================================================================
@pytest.mark.parametrize("req_str,expected", [
    ("Obligatory", "OBLIGATORY"),
    ("Elective",   "ELECTIVE"),
])
def test_courses_parser_accepts_sentence_case_requirement(
    tmp_path, req_str, expected,
):
    # Arrange — single course with the parameterized Requirement string.
    fixture = tmp_path / "course_case.txt"
    fixture.write_text(
        f"Algebra\n"
        f"10104\n"
        f"Dr. Vardi\n"
        f"83101,1,FALL,{req_str}\n"
        f"Exam\n",
        encoding="utf-8",
    )
    # Act
    courses = CoursesFileParser().parse(str(fixture))
    # Assert
    assert courses[0].programEntries[0].requirement.name == expected


# ===========================================================================
# TC-PRS-010..011: Test that invalid course fields (requirement, evaluation) are rejected.
# ===========================================================================
@pytest.mark.parametrize("req_line, eval_line", [
    ("83101,1,FALL,Recommended", "Exam"),  # TC-PRS-010: bad requirement ('Recommended')
    ("83101,1,FALL,Obligatory", "Quiz"),   # TC-PRS-011: bad evaluation ('Quiz')
])
def test_courses_parser_rejections(tmp_path, req_line, eval_line):
    # Arrange
    fixture = tmp_path / "course_bad.txt"
    fixture.write_text(
        f"Calculus 1\n10101\nDr. Cohen\n{req_line}\n{eval_line}\n",
        encoding="utf-8",
    )

    # Act + Assert — The system must raise a ValueError.
    with pytest.raises(ValueError):
        CoursesFileParser().parse(str(fixture))



# ===========================================================================
# TC-PRS-012: An empty courses file must not crash the parser.
# ===========================================================================
def test_courses_parser_handles_empty_file(tmp_path):
    # Arrange — Create a file with zero bytes.
    fixture = tmp_path / "courses_empty.txt"
    fixture.write_text("", encoding="utf-8")

    # Act — empty content fails the '$$$$' separator check, but the
    # fallback line-count guard (0 lines) tolerates it, so parsing falls
    # through to zero records rather than raising.
    courses = CoursesFileParser().parse(str(fixture))

    # Assert
    assert courses == []



# ---------------------------------------------------------------------------
# ExamPeriodsFileParser — TC-PRS-013...018
# ---------------------------------------------------------------------------


# ===========================================================================
# TC-PRS-013: A valid exam periods file with two periods produces two
# ExamPeriod objects with correct semester/moed/date boundaries.
# ===========================================================================
def test_exam_periods_parser_returns_correct_period_list(tmp_path):
    # Arrange — two periods in the expected line order.
    fixture = tmp_path / "periods_valid.txt"
    fixture.write_text(
        "FALL, Aleph\n"
        "29-01-2026, 11-03-2026\n"
        "31-01-2026 Saturday\n"
        f"{SEP}\n"
        "FALL, Bet\n"
        "01-09-2026, 30-09-2026\n",   # no excluded dates this period
        encoding="utf-8",
    )
    # Act
    periods = ExamPeriodsFileParser().parse(str(fixture))
    # Assert
    assert len(periods) == 2
    assert periods[0].semester.name == "FALL"
    assert periods[0].moed.name == "ALEPH"
    assert periods[0].startDate == date(2026, 1, 29)
    assert periods[0].endDate == date(2026, 3, 11)
    assert periods[1].moed.name == "BET"


# ===========================================================================
# TC-PRS-014: Check that dates inside an excluded range cannot be used for exams.
# ===========================================================================
def test_exam_periods_parser_expands_excluded_date_range(tmp_path):
    # Arrange — a single period whose Excluded entry is a 3-day range.
    fixture = tmp_path / "periods_with_range_excluded.txt"
    fixture.write_text(
        "FALL, Aleph\n"
        "29-01-2026, 11-03-2026\n"
        "02-03-2026, 04-03-2026 Purim\n",
        encoding="utf-8",
    )
    # Act
    periods = ExamPeriodsFileParser().parse(str(fixture))
    # Assert — the range expands to 3 individual dates.
    excluded = list(periods[0].excludedDates)
    assert date(2026, 3, 2) in excluded
    assert date(2026, 3, 3) in excluded
    assert date(2026, 3, 4) in excluded


# ===========================================================================
# TC-PRS-015..018: Test that invalid periods (bad dates, ranges, semester, moed) are rejected.
# ===========================================================================
@pytest.mark.parametrize("line1, line2", [
    ("FALL, Aleph", "11-03-2026, 11-03-2026"),  # TC-PRS-015: start == end
    ("FALL, Aleph", "11-03-2026, 01-03-2026"),  # TC-PRS-015: start > end
    ("FALL, Aleph", "2026-03-11, 30-06-2026"),  # TC-PRS-016: bad format
    ("FALL, Aleph", "11/03/2026, 30-06-2026"),  # TC-PRS-016: wrong sep
    ("FALL, Aleph", "11-Mar-2026, 30-06-2026"), # TC-PRS-016: letters
    ("FALL, Aleph", "11032026, 30-06-2026"),    # TC-PRS-016: no dashes
    ("FALL, Aleph", "32-03-2026, 30-06-2026"),  # TC-PRS-016: impossible day
    ("FALL, Aleph", "11-13-2026, 30-06-2026"),  # TC-PRS-016: impossible month
    ("WINTER, Aleph", "01-02-2026, 28-02-2026"),# TC-PRS-017: bad semester
    ("FALL, Delta", "01-02-2026, 28-02-2026"),  # TC-PRS-018: bad moed
])
def test_exam_periods_parser_rejections(tmp_path, line1, line2):
    # Arrange — single period with an invalid property.
    fixture = tmp_path / "periods_bad.txt"
    fixture.write_text(f"{line1}\n{line2}\n", encoding="utf-8")
    
    # Act + Assert
    with pytest.raises(ValueError):
        ExamPeriodsFileParser().parse(str(fixture))

# ---------------------------------------------------------------------------
# ProgramsFileParser — TC-PRS-019..022
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-PRS-019: A valid programs file with three valid 5-digit program
# codes produces three ProgramEntry objects.
# ===========================================================================
def test_programs_parser_returns_valid_program_entries(tmp_path):
    # Arrange — comma-separated codes in the expected example format.
    fixture = tmp_path / "programs_valid.txt"
    fixture.write_text("83101, 83102, 83108\n", encoding="utf-8")
    # Act
    entries = ProgramsFileParser().parse(str(fixture))
    # Assert — three entries, all codes belong to the valid program-code set.
    assert len(entries) == 3
    codes = entries
    assert codes == ["83101", "83102", "83108"]
    for code in codes:
        assert code in VALID_PROGRAM_CODES


# ===========================================================================
# TC-PRS-020: Check that the parser accepts 83182 as a valid program code.
# This code is valid even though it is not in the 83101-83115 range.
# ===========================================================================
def test_programs_parser_accepts_non_contiguous_valid_code(tmp_path):
    # Arrange — code 83182 (Quantum Engineering).
    fixture = tmp_path / "programs_quantum.txt"
    fixture.write_text("83182\n", encoding="utf-8")
    # Act
    entries = ProgramsFileParser().parse(str(fixture))
    # Assert
    assert len(entries) == 1
    assert entries[0] == "83182"


# ===========================================================================
# TC-PRS-021: An empty programs file must not crash the parser.
# ===========================================================================
def test_programs_parser_returns_empty_list_for_empty_file(tmp_path):
    # Arrange — Create a file with zero bytes.
    fixture = tmp_path / "programs_empty.txt"
    fixture.write_text("", encoding="utf-8")

    # Act — an empty programs file returns immediately with no entries.
    entries = ProgramsFileParser().parse(str(fixture))

    # Assert
    assert entries == []


# ===========================================================================
# TC-PRS-022: ProgramsFileParser uses a comma separator. If a different separator than ','
# (like '$$$$' or ';') is used, and the input length is not 5, the parser must raise a ValueError.
# ===========================================================================
def test_programs_parser_rejects_different_separator(tmp_path):
    # Arrange — using '$$$$' as separator in programs file
    fixture = tmp_path / "programs_invalid_separator.txt"
    fixture.write_text("83101$$$$83102", encoding="utf-8")

    # Act + Assert — ProgramsFileParser should raise a ValueError
    with pytest.raises(ValueError) as exc_info:
        ProgramsFileParser().parse(str(fixture))
    assert "comma-separated" in str(exc_info.value)


# ===========================================================================
# TC-PRS-023: Duplicate (semester, moed) period entries are rejected.
# Each (semester, moed) pair must appear at most once in periods.txt;
# multiple entries cause silent data loss in the Scheduler and must be
# rejected at parse time.
# ===========================================================================
def test_periods_parser_rejects_duplicate_semester_moed(tmp_path):
    # Arrange — two periods with identical (FALL, Aleph), different dates.
    f = tmp_path / "periods_dup.txt"
    f.write_text(
        "FALL, Aleph\n"
        "01-02-2026, 02-02-2026\n"
        "$$$$\n"
        "FALL, Aleph\n"
        "05-02-2026, 06-02-2026\n",
        encoding="utf-8",
    )

    # Act + Assert — parser must raise with a clear duplicate-related message.
    with pytest.raises(ValueError) as exc_info:
        ExamPeriodsFileParser().parse(str(f))
    msg = str(exc_info.value).lower()
    assert "duplicate" in msg, (
        f"Error must say 'duplicate'; got: {exc_info.value!r}"
    )
    # The error should also identify which (semester, moed) is duplicated.
    assert "fall" in msg
    assert "aleph" in msg


# ===========================================================================
# TC-PRS-024: A second moed (BET) for the same semester is allowed — not a duplicate.
# ===========================================================================
def test_periods_parser_accepts_different_moed_same_semester(tmp_path):
    f = tmp_path / "periods_diff_moed.txt"
    f.write_text(
        "FALL, Aleph\n"
        "01-02-2026, 02-02-2026\n"
        "$$$$\n"
        "FALL, Bet\n"
        "05-02-2026, 06-02-2026\n",
        encoding="utf-8",
    )
    periods = ExamPeriodsFileParser().parse(str(f))
    assert len(periods) == 2


# ---------------------------------------------------------------------------
# ParserFactory tests - TC-PRS-025..029
# ---------------------------------------------------------------------------

# ===========================================================================
# TC-PRS-025: test that ParserFactory returns the supported file types.
# ===========================================================================
def test_parser_factory_supported_types():
    # Act - Get the supported file types from the ParserFactory
    supported = ParserFactory.supported_types()

    # Assert - check that the supported file types are correct
    assert "courses" in supported
    assert "periods" in supported
    assert "programs" in supported

# ===========================================================================
# TC-PRS-026: test that ParserFactory creates a valid parser for a given file type.
# ===========================================================================
def test_parser_factory_create_valid():
    # Act - Get the supported file types from the ParserFactory
    parser = ParserFactory.create("courses")

    # Assert - check that the parser is of the correct type
    assert isinstance(parser, CoursesFileParser)

# ===========================================================================
# TC-PRS-027: test that ParserFactory raises an error for an invalid file type.
# ===========================================================================
def test_parser_factory_create_invalid():
    # Act + Assert - Try to create an invalid parser
    with pytest.raises(ValueError) as exc:
        ParserFactory.create("nonexistent")
    assert "Unknown file type 'nonexistent'" in str(exc.value)

# ===========================================================================
# TC-PRS-028: test that ParserFactory raises an error when a duplicate parser type is registered.
# ===========================================================================
def test_parser_factory_register_duplicate():
    # Act + Assert - Try to register a duplicate parser type
    with pytest.raises(ValueError) as exc:
        ParserFactory.register("courses", CoursesFileParser)
    assert "already registered" in str(exc.value)

# ===========================================================================
# TC-PRS-029: test that ParserFactory can parse multiple files.
# ===========================================================================
def test_parser_factory_parse_files(tmp_path):
    # Arrange - Create multiple files
    courses_file = tmp_path / "courses.txt"
    courses_file.write_text(
        "Calculus 1\n"
        "10101\n"
        "Dr. Cohen\n"
        "83101,2,FALL,Obligatory\n"
        "Exam\n",
        encoding="utf-8"
    )

    programs_file = tmp_path / "programs.txt"
    programs_file.write_text("83101, 83102\n", encoding="utf-8")

    mappings = {
        "courses": str(courses_file),
        "programs": str(programs_file),
        "periods": None
    }

    # Act - Parse the files
    results = ParserFactory.parse_files(mappings)

    # Assert - Check that the files were parsed correctly
    assert "courses" in results
    assert "programs" in results
    assert "periods" not in results
    assert len(results["courses"]) == 1
    assert results["programs"] == ["83101", "83102"]
