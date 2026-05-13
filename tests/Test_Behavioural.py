from datetime import date
import pytest

from src.models.enums import EvalType, Semester, Moed, Requirement
from src.logic.scheduler.scheduler import Scheduler
from src.logic.scheduler.checkers import (
    ProgramYearConflictChecker,
    ExcludedDatesChecker,
    ExamPeriodBoundaryChecker,
)


# Helper: Create the standard checkers and give them the exam dates.
def _default_checkers(periods):
    return [
        ProgramYearConflictChecker(),
        ExcludedDatesChecker(periods),
        ExamPeriodBoundaryChecker(periods),
    ]


def _schedule_signature(schedule):
    """
    Helper: Creates a unique 'fingerprint' for a schedule. 
    If two schedules have the exact same exams on the exact same dates, 
    they will get the same fingerprint. This helps us find duplicates.
    """
    return frozenset(
        (a.course.courseId, a.date, a.moed) for a in schedule.assignments
    )


# ===========================================================================
# TC-BEH-001 — Test that the system does not return duplicate schedules.
# ===========================================================================

# TC-BEH-001: The system must never return the exact same schedule twice.
def test_beh_001_no_duplicate_schedules_in_result(
    make_course, make_program_entry, make_period,
):
    # Arrange — 2 mandatory courses and 3 available days. 
    # The system should find 6 unique schedules.
    pe = make_program_entry(
        program_id="83101", year=2, requirement=Requirement.OBLIGATORY,
    )
    courses = [
        make_course(course_id="10101", name="A", program_entries=[pe]),
        make_course(course_id="10102", name="B", program_entries=[pe]),
    ]
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 3), excluded=[]
    )
    scheduler = Scheduler(
        courses=courses,
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )

    # Act — Run the scheduler.
    schedules = scheduler.generateAllSchedules()

    # Assert — Check that every schedule has a different fingerprint.
    signatures = [_schedule_signature(s) for s in schedules]
    assert len(signatures) == len(set(signatures)), (
        f"Duplicate schedules detected: produced {len(signatures)} schedules "
        f"but only {len(set(signatures))} are unique"
    )


# ===========================================================================
# TC-BEH-002 — Test that every single schedule is truly conflict-free.
# ===========================================================================

# TC-BEH-002: Make sure that no bad schedules slipped into the final results.
def test_beh_002_every_schedule_passes_all_conflict_checks(
    make_course, make_program_entry, make_period,
):
    # Arrange — 3 courses and 5 days, mixing mandatory and elective courses.
    pe1 = make_program_entry(
        program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    pe2 = make_program_entry(
        program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    courses = [
        make_course(course_id="10101", program_entries=[pe1]),
        make_course(course_id="10102", program_entries=[pe1]),
        make_course(course_id="10103", program_entries=[pe2]),
    ]
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 5), excluded=[]
    )
    checkers = _default_checkers([period])
    scheduler = Scheduler(
        courses=courses,
        periods=[period],
        conflictCheckers=checkers,
        validators=[],
    )

    # Act
    schedules = scheduler.generateAllSchedules()

    # Assert — Go through every exam in every schedule and ask the 
    # checkers if there is a conflict. None of them should fail.
    # Local import
    from src.models.domain import ExamSchedule
    assert len(schedules) > 0, "Sanity: scheduler should produce results"
    for s in schedules:
        partial = ExamSchedule()
        for assignment in s.assignments:
            for checker in checkers:
                conflict = checker.check(assignment, partial)
                assert conflict is False, (
                    f"Schedule contains assignment {assignment.course.courseId} "
                    f"on {assignment.date} that conflicts per "
                    f"{type(checker).__name__}"
                )
            partial.addAssignment(assignment)


# ===========================================================================
# TC-BEH-004 — Test that elective courses across programs CAN share a date.
# ===========================================================================

# TC-BEH-004: Two elective courses from different programs ARE allowed to be on the same day.
def test_beh_004_elective_courses_across_programs_may_share_date(
    make_course, make_program_entry, make_period,
):
    # Arrange — Two elective courses in year 2, different programs.
    pe_prog1 = make_program_entry(
        program_id="83101", year=2, requirement=Requirement.ELECTIVE)
    pe_prog2 = make_program_entry(
        program_id="83102", year=2, requirement=Requirement.ELECTIVE)
    course_a = make_course(course_id="10101", program_entries=[pe_prog1])
    course_b = make_course(course_id="10102", program_entries=[pe_prog2])
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 3), excluded=[]
    )
    scheduler = Scheduler(
        courses=[course_a, course_b],
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )

    # Act
    schedules = scheduler.generateAllSchedules()

    # Assert — Make sure there is at least one schedule where both 
    # electives are on the exact same day.
    same_date_schedules = []
    for s in schedules:
        date_a = next(a.date for a in s.assignments if a.course.courseId == "10101")
        date_b = next(a.date for a in s.assignments if a.course.courseId == "10102")
        if date_a == date_b:
            same_date_schedules.append(s)

    assert len(same_date_schedules) > 0, (
        "ELECTIVE courses in different programs were never scheduled on "
        "the same date — the elective exception was over-applied as a "
        "conflict"
    )


# ===========================================================================
# TC-BEH-005 — Test that Moed Aleph and Moed Bet do not affect each other.
# ===========================================================================

# Moed Aleph and Moed Bet are completely separate. If a date is blocked 
# in Aleph, it can still be used in Bet.
def test_beh_005_cross_moed_independence(
    make_course, make_program_entry, make_period,
):
    # Arrange — Exclude June 5 in Aleph, but ALLOW it in Bet.
    pe = make_program_entry(
        program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course = make_course(course_id="10101", program_entries=[pe])

    period_aleph = make_period(
        semester=Semester.FALL, moed=Moed.ALEPH,
        start=date(2026, 6, 1), end=date(2026, 6, 10),
        excluded=[date(2026, 6, 5)],   # June 5 excluded in ALEPH
    )
    period_bet = make_period(
        semester=Semester.FALL, moed=Moed.BET,
        start=date(2026, 6, 1), end=date(2026, 6, 10),
        excluded=[],                    # June 5 ALLOWED in BET
    )

    scheduler = Scheduler(
        courses=[course],
        periods=[period_aleph, period_bet],
        conflictCheckers=_default_checkers([period_aleph, period_bet]),
        validators=[],
    )

    # Act
    schedules = scheduler.generateAllSchedules()

    # Assert — Check that June 5 is used in Bet, but NEVER used in Aleph.
    aleph_june5 = [
        a for s in schedules for a in s.assignments
        if a.moed == Moed.ALEPH and a.date == date(2026, 6, 5)
    ]
    bet_june5 = [
        a for s in schedules for a in s.assignments
        if a.moed == Moed.BET and a.date == date(2026, 6, 5)
    ]

    assert len(aleph_june5) == 0, (
        "Moed ALEPH excluded June 5, yet engine produced an assignment "
        "for that date in ALEPH"
    )
    assert len(bet_june5) > 0, (
        "Moed BET does not exclude June 5, yet engine never used it — "
        "Moed ALEPH's exclusion leaked into BET (Moeds are not independent)"
    )


# ===========================================================================
# TC-BEH-006 — Test that the system tries other days (Backtracking).
# ===========================================================================

# TC-BEH-006: The system must not give up if the first try fails. It must go back 
# and try other dates until it finds a solution.
def test_beh_006_engine_backtracks_to_next_candidate(
    make_course, make_program_entry, make_period,
):
    # Arrange — 2 mandatory courses and 2 days. The system might try to 
    # put both on day 1 and fail. It must try day 2 instead of giving up.
    pe = make_program_entry(
        program_id="83101", year=2, requirement=Requirement.OBLIGATORY)
    course_a = make_course(course_id="10101", program_entries=[pe])
    course_b = make_course(course_id="10102", program_entries=[pe])
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 2), excluded=[]
    )
    scheduler = Scheduler(
        courses=[course_a, course_b],
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )

    # Act
    schedules = scheduler.generateAllSchedules()

    # Assert — Make sure it found the solutions and didn't crash.
    assert len(schedules) >= 1, (
        "Engine produced zero schedules even though a valid arrangement "
        "exists by backtracking — engine likely gave up after first conflict"
    )
    # Make sure both courses are on different days.
    for s in schedules:
        date_a = next(a.date for a in s.assignments if a.course.courseId == "10101")
        date_b = next(a.date for a in s.assignments if a.course.courseId == "10102")
        assert date_a != date_b, (
            "Schedule assigns both courses to the same date — engine "
            "produced a conflicting result instead of backtracking"
        )