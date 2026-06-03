from datetime import date
import pytest

from src.models.enums import EvalType, Semester, Moed, Requirement
from src.logic.SlotBuilder import SlotBuilder


# ===========================================================================
# TC-SLOT-001: SlotBuilder scores and sorts slots by difficulty.
# ===========================================================================
def test_slot_builder_scores_and_sorts_slots_by_difficulty(
    make_course, make_program_entry, make_period,
):
    # Arrange — Course A has an Obligatory program entry (higher difficulty, score 3)
    pe_ob = make_program_entry(program_id="83101", requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="10101", program_entries=[pe_ob])

    # Course B has an Elective program entry (lower difficulty, score 1)
    pe_el = make_program_entry(program_id="83101", requirement=Requirement.ELECTIVE)
    course_b = make_course(course_id="10102", program_entries=[pe_el])

    period = make_period(semester=Semester.FALL, moed=Moed.ALEPH)

    # Act
    slots = SlotBuilder([period], selected_programs=["83101"]).build([course_b, course_a])

    # Assert — Course A (higher score) should be sorted first, even though course B was passed first
    assert len(slots) == 2
    assert slots[0].course.courseId == "10101"
    assert slots[1].course.courseId == "10102"


# ===========================================================================
# TC-SLOT-002: SlotBuilder filters courses by selected programs.
# ===========================================================================
def test_slot_builder_filters_courses_by_selected_programs(
    make_course, make_program_entry, make_period,
):
    # Arrange — Course A is in selected program 83101
    pe_a = make_program_entry(program_id="83101")
    course_a = make_course(course_id="10101", program_entries=[pe_a])

    # Course B is in program 83102, which is NOT selected
    pe_b = make_program_entry(program_id="83102")
    course_b = make_course(course_id="10102", program_entries=[pe_b])

    period = make_period(semester=Semester.FALL, moed=Moed.ALEPH)

    # Act
    slots = SlotBuilder([period], selected_programs=["83101"]).build([course_a, course_b])

    # Assert — Only Course A should have slots built
    assert len(slots) == 1
    assert slots[0].course.courseId == "10101"


# ===========================================================================
# TC-SLOT-003: SlotBuilder populates candidate dates from periods.
# ===========================================================================
def test_slot_builder_populates_candidate_dates_from_periods(
    make_course, make_program_entry, make_period,
):
    # Arrange — period with some dates and an excluded date
    pe = make_program_entry(program_id="83101")
    course = make_course(course_id="10101", program_entries=[pe])
    period = make_period(
        semester=Semester.FALL,
        moed=Moed.ALEPH,
        start=date(2026, 6, 1),
        end=date(2026, 6, 5),
        excluded=[date(2026, 6, 3)],
    )

    # Act
    slots = SlotBuilder([period], selected_programs=["83101"]).build([course])

    # Assert
    assert len(slots) == 1
    assert slots[0].candidateDates == [
        date(2026, 6, 1),
        date(2026, 6, 2),
        date(2026, 6, 4),
        date(2026, 6, 5),
    ]


# ===========================================================================
# TC-SLOT-004: SlotBuilder builds slots for all available moeds.
# ===========================================================================
def test_slot_builder_builds_slots_for_all_available_moeds(
    make_course, make_program_entry, make_period,
):
    # Arrange — Course A has program entries in Fall semester. We define Fall Moed Aleph and Fall Moed Bet.
    pe = make_program_entry(program_id="83101", semester=Semester.FALL)
    course = make_course(course_id="10101", program_entries=[pe])

    period_aleph = make_period(semester=Semester.FALL, moed=Moed.ALEPH)
    period_bet = make_period(semester=Semester.FALL, moed=Moed.BET)

    # Act
    slots = SlotBuilder([period_aleph, period_bet], selected_programs=["83101"]).build([course])

    # Assert — 2 slots should be created: one for ALEPH, one for BET
    assert len(slots) == 2
    moeds = {s.moed for s in slots}
    assert moeds == {Moed.ALEPH, Moed.BET}


# ===========================================================================
# TC-SLOT-005: SlotBuilder handles course with multiple semesters.
# ===========================================================================
def test_slot_builder_handles_course_with_multiple_semesters(
    make_course, make_program_entry, make_period,
):
    # Arrange — Course A has Fall and Spring program entries
    pe_fall = make_program_entry(program_id="83101", semester=Semester.FALL)
    pe_spri = make_program_entry(program_id="83101", semester=Semester.SPRI)
    course = make_course(course_id="10101", program_entries=[pe_fall, pe_spri])

    period_fall = make_period(semester=Semester.FALL, moed=Moed.ALEPH)
    period_spri = make_period(semester=Semester.SPRI, moed=Moed.ALEPH)

    # Act
    slots = SlotBuilder([period_fall, period_spri], selected_programs=["83101"]).build([course])

    # Assert — 2 slots should be created: one for FALL, one for SPRI
    assert len(slots) == 2
    semesters = {s.semester for s in slots}
    assert semesters == {Semester.FALL, Semester.SPRI}


# ===========================================================================
# TC-SLOT-006: SlotBuilder handles empty course list.
# ===========================================================================
def test_slot_builder_handles_empty_course_list(make_period):
    # Arrange
    period = make_period(semester=Semester.FALL, moed=Moed.ALEPH)
    # Act
    slots = SlotBuilder([period]).build([])
    # Assert
    assert slots == []


# ===========================================================================
# TC-SLOT-007: SlotBuilder rejects missing period for required course semester.
# ===========================================================================
def test_slot_builder_rejects_missing_period_for_required_course_semester(
    make_course, make_program_entry, make_period,
):
    # Arrange — course has a FALL entry, but we only define a SPRI period
    pe = make_program_entry(program_id="83101", semester=Semester.FALL)
    course = make_course(course_id="10101", program_entries=[pe])
    period_spri = make_period(semester=Semester.SPRI, moed=Moed.ALEPH)

    # Act & Assert
    with pytest.raises(ValueError) as excinfo:
        SlotBuilder([period_spri], selected_programs=["83101"]).build([course])
    
    assert "no exam period is defined for that semester" in str(excinfo.value)


# ===========================================================================
# TC-SLOT-008: SlotBuilder ignores non-exam courses.
# ===========================================================================
def test_slot_builder_ignores_non_exam_courses(
    make_course, make_program_entry, make_period,
):
    # Arrange — Course has PROJECT evaluation, not EXAM
    pe = make_program_entry(program_id="83101", semester=Semester.FALL)
    course = make_course(
        course_id="10101",
        evaluation=EvalType.PROJECT,
        program_entries=[pe],
    )
    period = make_period(semester=Semester.FALL, moed=Moed.ALEPH)

    # Act
    slots = SlotBuilder([period], selected_programs=["83101"]).build([course])

    # Assert
    assert slots == []


# ===========================================================================
# TC-SLOT-009: SlotBuilder ignores courses unrelated to selected programs.
# ===========================================================================
def test_slot_builder_ignores_courses_unrelated_to_selected_programs(
    make_course, make_program_entry, make_period,
):
    # Arrange — Course has entry for program 83102, but we select 83101
    pe = make_program_entry(program_id="83102", semester=Semester.FALL)
    course = make_course(course_id="10101", program_entries=[pe])
    period = make_period(semester=Semester.FALL, moed=Moed.ALEPH)

    # Act
    slots = SlotBuilder([period], selected_programs=["83101"]).build([course])

    # Assert
    assert slots == []
