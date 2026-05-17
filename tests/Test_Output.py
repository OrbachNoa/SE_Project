from datetime import date
import os
import pytest

from src.models.enums import EvalType, Semester, Moed, Requirement
from src.models.domain import ExamSchedule
from src.writers.textFileWriter import TextFileWriter


# ---------------------------------------------------------------------------
# TC-OUT-001 — Test that the date uses the DD-MM-YYYY format.
# ---------------------------------------------------------------------------

# TC-OUT-001: The date June 5, 2026 should look like '05-06-2026' in the output file.
def test_format_schedule_uses_dd_mm_yyyy_date_format(
    make_assignment, empty_schedule,
):
    # Arrange — A schedule with one exam on June 5, 2026.
    schedule = empty_schedule
    schedule.addAssignment(make_assignment(exam_date=date(2026, 6, 5)))
    # Act
    output = TextFileWriter().formatSchedule(schedule)
    # Assert — output contains the zero-padded DD-MM-YYYY date.
    assert "05-06-2026" in output
    # And not the swapped MM-DD form.
    assert "06-05-2026" not in output or "05-06-2026" in output


# ---------------------------------------------------------------------------
# TC-OUT-002 — Test that headers for Semester and Moed are in the output.
# ---------------------------------------------------------------------------

# TC-OUT-002: The output file should show the names of the Semester and the Moed as headers.
def test_format_schedule_contains_semester_and_moed_section_headers(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange — Create exams for different Semesters and Moeds
    schedule = empty_schedule
    pe_fall = make_program_entry(semester=Semester.FALL)
    pe_spri = make_program_entry(semester=Semester.SPRI)
    schedule.addAssignment(make_assignment(
        course=make_course(course_id="A", program_entries=[pe_fall]),
        exam_date=date(2026, 6, 5), moed=Moed.ALEPH,
    ))
    schedule.addAssignment(make_assignment(
        course=make_course(course_id="B", program_entries=[pe_fall]),
        exam_date=date(2026, 9, 5), moed=Moed.BET,
    ))
    schedule.addAssignment(make_assignment(
        course=make_course(course_id="C", program_entries=[pe_spri]),
        exam_date=date(2026, 2, 5), moed=Moed.ALEPH,
    ))
    # Act
    output = TextFileWriter().formatSchedule(schedule)
    # Assert — Check that the names of Semesters and Moeds are present.
    out_upper = output.upper()
    assert "FALL" in out_upper
    assert "SPRI" in out_upper
    assert "ALEPH" in out_upper
    assert "BET" in out_upper


# ---------------------------------------------------------------------------
# TC-OUT-003 — Test that an empty schedule does not crash the system.
# ---------------------------------------------------------------------------

# TC-OUT-003: If a schedule has no exams, the system should still return a string.
def test_format_schedule_handles_empty_schedule_without_crashing(empty_schedule):
    # Arrange — already an empty schedule.
    # Act
    output = TextFileWriter().formatSchedule(empty_schedule)
    # Assert — Output should be a string, not None.
    assert output is not None
    assert isinstance(output, str)


# ---------------------------------------------------------------------------
# TC-OUT-004 — Test that the system creates a file on the computer.
# ---------------------------------------------------------------------------

# TC-OUT-004: Verify that the write() function actually creates a file at the given path.
def test_write_creates_file_at_specified_path(
    tmp_path, make_assignment, empty_schedule,
):
    # Arrange — Create a path for the output file.
    schedule = empty_schedule
    schedule.addAssignment(make_assignment(exam_date=date(2026, 6, 5)))
    output_path = tmp_path / "schedule.txt"

    writer = TextFileWriter()
    # Act — Write the schedule to the file.
    writer.write([schedule], str(output_path))
    # Assert — Verify the file exists and has the correct date inside.
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "05-06-2026" in content


# ---------------------------------------------------------------------------
# TC-OUT-005 — formatSchedule sorts assignments by date within section.
# ---------------------------------------------------------------------------

# Inside each section, the dates should appear in order (earliest first).
def test_format_schedule_sorts_assignments_by_date_within_section(
    make_course, make_program_entry, make_assignment, empty_schedule,
):
    # Arrange — Add three exams out of order: June 20, then 5, then 12.
    schedule = empty_schedule
    pe = make_program_entry(semester=Semester.FALL)
    for d in [date(2026, 6, 20), date(2026, 6, 5), date(2026, 6, 12)]:
        schedule.addAssignment(make_assignment(
            course=make_course(
                course_id=f"C{d.day}", program_entries=[pe]),
            exam_date=d, moed=Moed.ALEPH,
        ))
    # Act
    output = TextFileWriter().formatSchedule(schedule)
    # Assert — Check that June 5 is before June 12, and 12 is before 20.
    i5 = output.find("05-06-2026")
    i12 = output.find("12-06-2026")
    i20 = output.find("20-06-2026")
    assert i5 != -1 and i12 != -1 and i20 != -1
    assert i5 < i12 < i20


# ---------------------------------------------------------------------------
# TC-OUT-006 — formatSchedule includes instructor name.
# ---------------------------------------------------------------------------


# The output file must show the name of the teacher for each exam.
def test_format_schedule_includes_instructor_name(
    make_course, make_assignment, empty_schedule,
):
    # Arrange — Create a course with a specific instructor name.
    schedule = empty_schedule
    schedule.addAssignment(make_assignment(
        course=make_course(instructor="Dr. Distinctive-Name"),
        exam_date=date(2026, 6, 5),
    ))
    # Act
    output = TextFileWriter().formatSchedule(schedule)
    # Assert — Check that the name appears in the file.
    assert "Dr. Distinctive-Name" in output


    # ===========================================================================
# TC-OUT-007 — Semester sections in output appear in fixed enum order.
# Regression test for bug #3a: when SPRI dates fall before FALL dates,
# the output must still list FALL section before SPRI section
# (REQ-2.3.3: "separation between semester A (FALL) and semester B (SPRING)").
# ===========================================================================
def test_format_schedule_orders_fall_before_spri_regardless_of_dates(
    make_assignment, empty_schedule, make_course, make_program_entry,
):
    # Arrange — SPRI exam in Feb (earlier), FALL exam in July (later).
    spring_course = make_course(
        course_id="20001", name="Spring Course",
        program_entries=[make_program_entry(semester=Semester.SPRI)],
    )
    fall_course = make_course(
        course_id="20002", name="Fall Course",
        program_entries=[make_program_entry(semester=Semester.FALL)],
    )

    schedule = empty_schedule
    schedule.addAssignment(make_assignment(
        course=spring_course, exam_date=date(2026, 2, 1), moed=Moed.ALEPH,
    ))
    schedule.addAssignment(make_assignment(
        course=fall_course, exam_date=date(2026, 7, 1), moed=Moed.ALEPH,
    ))

    # Act
    out = TextFileWriter().formatSchedule(schedule)

    # Assert — FALL header must appear at a smaller index than SPRI header,
    # i.e. FALL is rendered FIRST even though its date is later.
    fall_pos = out.find("SEMESTER: FALL")
    spri_pos = out.find("SEMESTER: SPRI")
    assert fall_pos != -1, "FALL section missing from output"
    assert spri_pos != -1, "SPRI section missing from output"
    assert fall_pos < spri_pos, (
        f"FALL must appear before SPRI in output order "
        f"(got fall_pos={fall_pos}, spri_pos={spri_pos}).\n"
        f"Output was:\n{out}"
    )


# ===========================================================================
# TC-OUT-008 — Moed sections in output appear in fixed enum order
# (ALEPH → BET → GIMEL), regardless of date order in the input.
# Regression test for bug #3b.
# ===========================================================================
def test_format_schedule_orders_aleph_bet_gimel_regardless_of_dates(
    make_assignment, empty_schedule, make_course,
):
    # Arrange — GIMEL in January (earliest), ALEPH in February, BET in March.
    course = make_course(course_id="30001", name="Test Course")
    schedule = empty_schedule
    schedule.addAssignment(make_assignment(
        course=course, exam_date=date(2026, 1, 15), moed=Moed.GIMEL,
    ))
    schedule.addAssignment(make_assignment(
        course=course, exam_date=date(2026, 2, 15), moed=Moed.ALEPH,
    ))
    schedule.addAssignment(make_assignment(
        course=course, exam_date=date(2026, 3, 15), moed=Moed.BET,
    ))

    # Act
    out = TextFileWriter().formatSchedule(schedule)

    # Assert — ALEPH then BET then GIMEL, even though chronological order
    # would have placed GIMEL first.
    aleph_pos = out.find("MOED: ALEPH")
    bet_pos   = out.find("MOED: BET")
    gimel_pos = out.find("MOED: GIMEL")
    assert aleph_pos != -1 and bet_pos != -1 and gimel_pos != -1, (
        "All three moed sections must appear"
    )
    assert aleph_pos < bet_pos < gimel_pos, (
        f"Moed sections must appear in fixed order ALEPH→BET→GIMEL "
        f"(got aleph={aleph_pos}, bet={bet_pos}, gimel={gimel_pos}).\n"
        f"Output was:\n{out}"
    )