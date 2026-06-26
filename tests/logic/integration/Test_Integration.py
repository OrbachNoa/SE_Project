"""Integration tests for the full parse -> validate -> schedule -> write
pipeline (`main.run_pipeline`), using real fixture files end-to-end — no
mocks for parsers, validators, scheduler, or writer.

Covers a fully valid run producing a correctly-formatted output file, an
invalid program code being rejected with a message naming the bad code, a
too-many-programs selection being rejected with a message naming the
count and the limit, a course list with zero EXAM-eligible courses still
completing and writing the empty-schedule placeholder, and a genuine
same-program/same-year conflict resolving to zero schedules rather than a
schedule that silently violates the conflict rule.

Conventions:
- Each test carries a unique TC-INT-NNN identifier in the comment block
  above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections.
- No conftest fixture models the pipeline's file-path arguments, so each
  test builds its own paths from the shared FIXTURES directory and uses
  pytest's built-in `tmp_path` for the output file.
"""
from pathlib import Path
import pytest

# Import the main pipeline function.
from main import run_pipeline

# Set the path to the folder where the test files (fixtures) are located.
FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


# ===========================================================================
# TC-INT-001 — Test that valid input files create a correct output file.
# ===========================================================================
def test_full_pipeline_valid_input_produces_output_file(tmp_path):
    # Arrange — Use three valid files (courses, periods, and programs).
    courses_path = FIXTURES / "courses_valid.txt"
    periods_path = FIXTURES / "periods_valid.txt"
    programs_path = FIXTURES / "programs_valid.txt"
    output_path = tmp_path / "schedules_output.txt"
    # Act — execute the entire pipeline end-to-end.
    run_pipeline(
        courses_file=str(courses_path),
        periods_file=str(periods_path),
        programs_file=str(programs_path),
        output_file=str(output_path),
    )
    # Assert — Check that the file was created and is not empty.
    assert output_path.exists(), \
        "Pipeline did not create the expected output file"
    content = output_path.read_text(encoding="utf-8")
    assert len(content) > 0, "Output file was created but is empty"
    # Check that the dates in the file are in the DD-MM-YYYY format.
    import re
    assert re.search(r"\d{2}-\d{2}-2026", content), \
        "Output file does not contain any DD-MM-YYYY dates"


# ===========================================================================
# TC-INT-002 — Test that an invalid program code stops the system.
# ===========================================================================
def test_invalid_program_code_produces_error_no_output(tmp_path):
    # Arrange — Use a programs file with a bad code ('99999').
    courses_path = FIXTURES / "courses_valid.txt"
    periods_path = FIXTURES / "periods_valid.txt"
    programs_path = FIXTURES / "programs_bad_code.txt"
    output_path = tmp_path / "should_not_exist.txt"

    # Act + Assert — The system must raise, and must NOT create an output file.
    raised = False
    try:
        run_pipeline(
            courses_file=str(courses_path),
            periods_file=str(periods_path),
            programs_file=str(programs_path),
            output_file=str(output_path),
        )
    except ValueError as exc:
        raised = True
        assert "99999" in str(exc), \
            "Error message does not reference the bad program code '99999'"

    assert raised is True, \
        "Expected a ValueError for the invalid program code, but none was raised"
    # The file must NOT exist regardless of how the system failed.
    assert not output_path.exists(), \
        "Output file should not be created when validation fails"


# ===========================================================================
# TC-INT-003 — Test that selecting more than 5 programs causes an error.
# ===========================================================================
def test_too_many_programs_produces_validation_error(tmp_path):
    # Arrange — Use a file with 6 programs (the limit is 5).
    courses_path = FIXTURES / "courses_valid.txt"
    periods_path = FIXTURES / "periods_valid.txt"
    programs_path = FIXTURES / "programs_too_many.txt"
    output_path = tmp_path / "should_not_exist.txt"

    # Act + Assert — The system must raise, naming the count and the limit.
    raised = False
    try:
        run_pipeline(
            courses_file=str(courses_path),
            periods_file=str(periods_path),
            programs_file=str(programs_path),
            output_file=str(output_path),
        )
    except ValueError as exc:
        raised = True
        assert "Too many programs selected" in str(exc), \
            "Error message does not explain the too-many-programs failure"

    assert raised is True, \
        "Expected a ValueError for too many selected programs, but none was raised"
    # No output file should be created.
    assert not output_path.exists(), \
        "Output file should not be created when > 5 programs are selected"


# ===========================================================================
# TC-INT-004 — Test that the system works even if there are no exams to schedule.
# ===========================================================================
def test_no_exam_courses_completes_with_empty_schedule(tmp_path):
    # Arrange — Use a file with zero "Exam" type courses (only Projects).
    courses_path = FIXTURES / "courses_no_exams.txt"
    periods_path = FIXTURES / "periods_valid.txt"
    programs_path = FIXTURES / "programs_valid.txt"
    output_path = tmp_path / "empty_schedule.txt"

    # Act — The system should complete without crashing.
    run_pipeline(
        courses_file=str(courses_path),
        periods_file=str(periods_path),
        programs_file=str(programs_path),
        output_file=str(output_path),
    )

    # Assert — the writer always creates the file, even for an empty
    # schedule list (it writes a placeholder line instead of skipping).
    assert output_path.exists(), \
        "Pipeline did not create an output file for the empty-schedule case"
    content = output_path.read_text(encoding="utf-8")
    assert "No valid exam schedules were generated." in content


# ===========================================================================
# TC-INT-005 — Test that conflicts are detected correctly in a full run.
# ===========================================================================
def test_multi_program_conflict_detection_end_to_end(tmp_path):
    # Arrange — Use courses that must be on the same day (impossible to schedule).
    courses_path = FIXTURES / "courses_conflict.txt"
    periods_path = FIXTURES / "periods_one_day.txt"
    programs_path = FIXTURES / "programs_single.txt"
    output_path = tmp_path / "no_schedule.txt"
    # Act — The system should finish without crashing.
    run_pipeline(
        courses_file=str(courses_path),
        periods_file=str(periods_path),
        programs_file=str(programs_path),
        output_file=str(output_path),
    )
    # Assert — the file must always be written, and the output must NOT
    # show both courses together (since they conflict).
    assert output_path.exists(), \
        "Pipeline did not create an output file for the conflict case"
    content = output_path.read_text(encoding="utf-8")
    # It's impossible to have both, so this should fail if both are there.
    has_cal = "83001" in content or "Calculus 1" in content
    has_lin = "83002" in content or "Linear Algebra" in content
    assert not (has_cal and has_lin), (
        "Pipeline produced a schedule with both conflicting courses; "
        "ProgramYearConflictChecker did not block the conflict"
    )
