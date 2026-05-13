from datetime import date
import pytest

from src.parsers.fileParser import FileParser
from src.parsers.courseParser import CoursesFileParser
from src.parsers.dateParser import ExamPeriodsFileParser
from src.parsers.programParser import ProgramsFileParser

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


# ===========================================================================
# Abstract FileParser.validateSeparator() — TC-PRS-001..004
# ===========================================================================

# TC-PRS-001: validateSeparator accepts a well-formed '$$$$' separator
def test_validate_separator_accepts_valid_quad_dollar():
    # Arrange — two records separated by exactly '$$$$'.
    content = f"record_one\n{SEP}\nrecord_two"
    # Act
    result = FileParser.validateSeparator(content)
    # Assert
    assert result is True or result is None  # spec allows either


# TC-PRS-002: validateSeparator rejects content that contains no '$$$$'
def test_validate_separator_rejects_missing_separator():
    # Arrange — no separator anywhere.
    content = "record_one record_two no separator here"
    # Act + Assert
    # We expect a ValueError here because there is no '$$$$' separator.
    with pytest.raises(ValueError):
        FileParser.validateSeparator(content)


# TC-PRS-003: Surrounding whitespace around the separator must be handled consistently.
def test_validate_separator_tolerates_surrounding_whitespace():
    # Arrange — separator surrounded by spaces on its own line.
    content = f"record_one\n  {SEP}  \nrecord_two"
    # Act
    result = FileParser.validateSeparator(content)
    # Assert
    assert result is True or result is None


# TC-PRS-004: A partial separator (one, two, or three '$' signs) must NOT be accepted as a valid record separator.
@pytest.mark.parametrize("partial", ["$", "$$", "$$$"])
def test_validate_separator_rejects_partial_separator(partial):
    # Arrange — content uses fewer than four '$' signs between records.
    content = f"record_one\n{partial}\nrecord_two"
    # Act + Assert
    with pytest.raises(ValueError):
        FileParser.validateSeparator(content)


# ===========================================================================
# CoursesFileParser — TC-PRS-005..007
# ===========================================================================

# TC-PRS-005: A well-formed courses file with three records produces three Course objects whose key
# fields match the fixture exactly.
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


# TC-PRS-006: Check that the parser adds one program entry for each program line in the course.
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


# TC-PRS-007: Requirement and Evaluation
# field values appear in sentence case in the file ("Obligatory","Elective", "Exam", "Project", "Attendance").
# The parser must accept them in that form.

# Run the same test with different Requirement values.
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


# ---------------------------------------------------------------------------
# TC-PRS-008 — Test that invalid Requirement values are rejected.
# ---------------------------------------------------------------------------
# A course requirement must be either 'Obligatory' or 'Elective'.
# Anything else should cause an error.
def test_courses_parser_rejects_invalid_requirement(tmp_path):
    # Arrange — Create a course with a bad requirement ('Recommended').
    fixture = tmp_path / "course_bad_requirement.txt"
    fixture.write_text(
        "Calculus 1\n"
        "10101\n"
        "Dr. Cohen\n"
        "83101,1,FALL,Recommended\n"   
        "Exam\n",
        encoding="utf-8",
    )

    # Act + Assert — The system must raise a ValueError.
    with pytest.raises(ValueError):
        CoursesFileParser().parse(str(fixture))



# ---------------------------------------------------------------------------
# TC-PRS-009 — Test that invalid Evaluation values are rejected.
# ---------------------------------------------------------------------------
# A course evaluation must be 'Exam', 'Project', or 'Attendance'.
def test_courses_parser_rejects_invalid_evaluation(tmp_path):
    # Arrange — Create a course with a bad evaluation ('Quiz').
    fixture = tmp_path / "course_bad_evaluation.txt"
    fixture.write_text(
        "Calculus 1\n"
        "10101\n"
        "Dr. Cohen\n"
        "83101,1,FALL,Obligatory\n"
        "Quiz\n",                        
        encoding="utf-8",
    )

    # Act + Assert — The system must raise a ValueError.
    with pytest.raises(ValueError):
        CoursesFileParser().parse(str(fixture))



# ---------------------------------------------------------------------------
# TC-PRS-010 — Test that an empty courses file is handled properly.
# ---------------------------------------------------------------------------
# If the courses file has absolutely no text in it, the system should 
# either reject it safely or return an empty list. It must not crash.
def test_courses_parser_handles_empty_file(tmp_path):
    # Arrange — Create a file with zero bytes.
    fixture = tmp_path / "courses_empty.txt"
    fixture.write_text("", encoding="utf-8")

    # Act — Try to read the empty file.
    try:
        courses = CoursesFileParser().parse(str(fixture))
    except ValueError:
        return  # This is okay: the parser safely rejected the empty file.
    except Exception as e:
        pytest.fail(f"Empty courses file caused a crash: {e}")

    # Assert — If it didn't raise an error, it must return an empty list.
    assert courses == [] or len(courses) == 0



# ===========================================================================
# ExamPeriodsFileParser — TC-PRS-011...016
# ===========================================================================

# TC-PRS-011: A valid exam periods file with two periods produces two
# ExamPeriod objects with correct semester/moed/date boundaries.
def test_exam_periods_parser_returns_correct_period_list(tmp_path):
    # Arrange — two periods per SRS Appendix A line order.
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


# TC-PRS-012: Check that dates inside an excluded range cannot be used for exams.
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


# TC-PRS-013: An exam period whose start date is NOT strictly less than its end date must cause a parse error.
@pytest.mark.parametrize("start,end", [
    ("11-03-2026", "11-03-2026"),   # start == end  → invalid per SRS
    ("11-03-2026", "01-03-2026"),   # start  > end  → invalid per SRS
])
def test_exam_periods_parser_rejects_non_strict_date_range(tmp_path, start, end):
    # Arrange — single period with an invalid date range.
    fixture = tmp_path / "periods_bad_range.txt"
    fixture.write_text(
        f"FALL, Aleph\n{start}, {end}\n",
        encoding="utf-8",
    )
    # Act + Assert
    with pytest.raises(ValueError):
        ExamPeriodsFileParser().parse(str(fixture))


# TC-PRS-014: Invalid date formats — wrong order, letters, missing dashes — must cause a parse error.
@pytest.mark.parametrize("bad_date", [
    "2026-03-11",   # not DD-MM-YYYY
    "11/03/2026",   # wrong separator
    "11-Mar-2026",  # month as letters
    "11032026",     # missing dashes
    "32-03-2026",   # impossible day
    "11-13-2026",   # impossible month
])
def test_exam_periods_parser_rejects_invalid_date_formats(tmp_path, bad_date):
    # Arrange — single period whose start date is invalid.
    fixture = tmp_path / "periods_bad_date.txt"
    fixture.write_text(
        f"FALL, Aleph\n{bad_date}, 30-06-2026\n",
        encoding="utf-8",
    )
    # Act + Assert
    with pytest.raises(ValueError):
        ExamPeriodsFileParser().parse(str(fixture))

# ---------------------------------------------------------------------------
# TC-PRS-015 — Test that invalid Semester values are rejected.
# ---------------------------------------------------------------------------
# A semester must be 'FALL', 'SPRI', or 'SUMM'.
def test_exam_periods_parser_rejects_invalid_semester(tmp_path):
    # Arrange — Create a period with a bad semester ('WINTER').
    fixture = tmp_path / "periods_bad_semester.txt"
    fixture.write_text(
        "WINTER, Aleph\n01-02-2026, 28-02-2026\n",
        encoding="utf-8",
    )

    # Act + Assert — The system must raise a ValueError.
    with pytest.raises(ValueError):
        ExamPeriodsFileParser().parse(str(fixture))


# ---------------------------------------------------------------------------
# TC-PRS-016 — Test that invalid Moed values are rejected.
# ---------------------------------------------------------------------------
# A moed must be 'Aleph', 'Bet', or 'Gimel'.
def test_exam_periods_parser_rejects_invalid_moed(tmp_path):
    # Arrange — Create a period with a bad moed ('Delta').
    fixture = tmp_path / "periods_bad_moed.txt"
    fixture.write_text(
        "FALL, Delta\n01-02-2026, 28-02-2026\n",
        encoding="utf-8",
    )

    # Act + Assert — The system must raise a ValueError.
    with pytest.raises(ValueError):
        ExamPeriodsFileParser().parse(str(fixture))

# ===========================================================================
# ProgramsFileParser — TC-PRS-017..020
# ===========================================================================

# TC-PRS-017: A valid programs file with three valid 5-digit program
# codes produces three ProgramEntry objects.
def test_programs_parser_returns_valid_program_entries(tmp_path):
    # Arrange — comma-separated codes per SRS §1.1 example format.
    fixture = tmp_path / "programs_valid.txt"
    fixture.write_text("83101, 83102, 83108\n", encoding="utf-8")
    # Act
    entries = ProgramsFileParser().parse(str(fixture))
    # Assert — three entries, all codes belong to the SRS valid set.
    assert len(entries) == 3
    codes = [e.programId for e in entries]
    assert codes == ["83101", "83102", "83108"]
    for code in codes:
        assert code in VALID_PROGRAM_CODES


# TC-PRS-018: Check that the parser accepts 83182 as a valid program code.
# This code is valid in the SRS, even though it is not in the 83101-83115 range.
def test_programs_parser_accepts_non_contiguous_valid_code(tmp_path):
    # Arrange — code 83182 (Quantum Engineering).
    fixture = tmp_path / "programs_quantum.txt"
    fixture.write_text("83182\n", encoding="utf-8")
    # Act
    entries = ProgramsFileParser().parse(str(fixture))
    # Assert
    assert len(entries) == 1
    assert entries[0].programId == "83182"


# TC-PRS-019: Check that an invalid program code raises an error with the bad code in the message.
@pytest.mark.parametrize("bad_code", [
    "99999",   # well outside any plausible range
    "83106",   # IN the 83101..83115 range, but NOT in SRS valid set
    "83110",   # also inside the 83101-83115 range, but not valid in the SRS list
    "83100",   # one below the lowest valid code
])
def test_programs_parser_rejects_unknown_code(tmp_path, bad_code):
    # Arrange — a single invalid code.
    fixture = tmp_path / "programs_bad.txt"
    fixture.write_text(bad_code + "\n", encoding="utf-8")

    # Act + Assert — the error message must reference the bad code.
    with pytest.raises(ValueError) as excinfo:
        ProgramsFileParser().parse(str(fixture))
    assert bad_code in str(excinfo.value)


# ---------------------------------------------------------------------------
# TC-PRS-020 — Test that an empty programs file is handled properly.
# ---------------------------------------------------------------------------
# If the programs file is completely empty, the system must not crash.
# It should safely reject it or return an empty list.
def test_programs_parser_rejects_empty_file(tmp_path):
    # Arrange — Create a file with zero bytes.
    fixture = tmp_path / "programs_empty.txt"
    fixture.write_text("", encoding="utf-8")

    # Act + Assert — Try to read the file.
    try:
        entries = ProgramsFileParser().parse(str(fixture))
    except ValueError:
        return  # This is okay: the parser rejected the empty file.
    except Exception as e:
        pytest.fail(f"Empty programs file caused a crash: {e}")

    # If it didn't raise an error, it must return an empty list.
    assert entries == [] or len(entries) == 0
