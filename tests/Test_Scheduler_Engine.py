from datetime import date
from unittest.mock import MagicMock
import pytest

from src.models.enums import EvalType, Semester, Moed, Requirement
from src.logic.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.ExcludedDatesChecker import ExcludedDatesChecker
from src.logic.ExamPeriodBoundaryChecker import ExamPeriodBoundaryChecker
from src.logic.Scheduler import Scheduler


# Helper: Creates the default checkers and gives them the exam dates they need.
def _default_checkers(periods):
    return [
        ProgramYearConflictChecker(),
        ExcludedDatesChecker(periods),
        ExamPeriodBoundaryChecker(periods),
    ]


# ---------------------------------------------------------------------------
# TC-ENG-001 — Test that simple input creates the correct number of schedules.
# ---------------------------------------------------------------------------

# TC-ENG-001: Two OBLIGATORY courses, same program/year, with three
# available dates — every pair of distinct dates is a valid schedule.
# The number of valid schedules is 3 * 2 = 6 (ordered pairs).
def test_generate_all_schedules_produces_expected_count(
    make_course, make_program_entry, make_period,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2,
                            requirement=Requirement.OBLIGATORY)
    c1 = make_course(course_id="10101", name="C1", program_entries=[pe])
    c2 = make_course(course_id="10102", name="C2", program_entries=[pe])
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 3), excluded=[]
    )

    scheduler = Scheduler(
        courses=[c1, c2],
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )
    # Act
    schedules = scheduler.generateAllSchedules()
    # Assert — We expect 6 different valid schedules.
    assert len(schedules) == 6


# ---------------------------------------------------------------------------
# TC-ENG-002 — Test that the system returns more than one schedule.
# ---------------------------------------------------------------------------

# TC-ENG-002: When there are many days and no conflicts, the system should find multiple valid schedules.
def test_generate_all_schedules_returns_multiple_solutions(
    make_course, make_program_entry, make_period,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2,
                            requirement=Requirement.OBLIGATORY)
    courses = [
        make_course(course_id=str(10100 + i), program_entries=[pe])
        for i in range(1, 4)
    ]
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 6), excluded=[]
    )
    scheduler = Scheduler(
        courses=courses,
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )
    # Act
    schedules = scheduler.generateAllSchedules()
    # Assert
    assert len(schedules) > 1


# ---------------------------------------------------------------------------
# TC-ENG-003 — Test that the system returns an empty list if no schedule is possible.
# ---------------------------------------------------------------------------

# TC-ENG-003: If two mandatory courses must be on the same day, they conflict.
# The system should return an empty list instead of crashing.
def test_generate_all_schedules_returns_empty_when_impossible(
    make_course, make_program_entry, make_period,
):
    # Arrange
    pe = make_program_entry(program_id="83101", year=2,
                            requirement=Requirement.OBLIGATORY)
    c1 = make_course(course_id="10101", program_entries=[pe])
    c2 = make_course(course_id="10102", program_entries=[pe])
    period = make_period(
        start=date(2026, 6, 1),
        end=date(2026, 6, 2),
        excluded=[date(2026, 6, 2)],
    )
    scheduler = Scheduler(
        courses=[c1, c2],
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )
    # Act + Assert — must not raise an exception.
    schedules = scheduler.generateAllSchedules()
    assert schedules == []


# ---------------------------------------------------------------------------
# TC-ENG-004 — Test that every schedule has all the required courses.
# ---------------------------------------------------------------------------

# TC-ENG-004: With four EXAM courses and six available dates, every
# returned schedule must contain exactly four assignments.
def test_every_returned_schedule_is_complete(
    make_course, make_program_entry, make_period,
):
    # Arrange — four EXAM courses, six dates, no conflicts forced.
    pe = make_program_entry(program_id="83101", year=2,
                            requirement=Requirement.OBLIGATORY)
    courses = [
        make_course(course_id=str(10100 + i), program_entries=[pe])
        for i in range(1, 5)
    ]
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 6), excluded=[]
    )
    scheduler = Scheduler(
        courses=courses,
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )
    # Act
    schedules = scheduler.generateAllSchedules()
    # Assert.
    assert len(schedules) > 0
    assert all(len(s.assignments) == 4 for s in schedules)


# ---------------------------------------------------------------------------
# TC-ENG-005 — Test that we can add a new type of conflict checker easily.
# ---------------------------------------------------------------------------

# TC-ENG-005: We can give the system a custom checker, and the system should use it to find conflicts.
def test_scheduler_uses_injected_custom_checker(
    make_course, make_program_entry, make_period,
):
    # Arrange — a custom checker that rejects EVERYTHING.
    class RejectAllChecker:
        def __init__(self):
            self.calls = 0

        def check(self, assignment, schedule):
            self.calls += 1
            return True  # always conflict

    rejector = RejectAllChecker()
    pe = make_program_entry(program_id="83101", year=2,
                            requirement=Requirement.OBLIGATORY)
    courses = [make_course(course_id="10101", program_entries=[pe])]
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 3), excluded=[]
    )

    scheduler = Scheduler(
        courses=courses,
        periods=[period],
        conflictCheckers=[rejector],   # ONLY the custom checker
        validators=[],
    )

    # Act
    schedules = scheduler.generateAllSchedules()
    # Assert — no schedules, AND the custom checker was actually called.
    assert schedules == []
    assert rejector.calls > 0


# ---------------------------------------------------------------------------
# TC-ENG-006 — Courses shared across programs scheduled exactly once.
# ---------------------------------------------------------------------------

# If a course is part of two different study programs, it should
# only appear once in the final schedule.
def test_courses_shared_across_programs_are_scheduled_once(
    make_course, make_program_entry, make_period,
):
    # Arrange — one course, two program entries referring to it.
    pe_a = make_program_entry(program_id="83101", year=2)
    pe_b = make_program_entry(program_id="83102", year=2)
    shared = make_course(
        course_id="10101",
        name="Shared Course",
        program_entries=[pe_a, pe_b],
    )
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 3), excluded=[]
    )
    scheduler = Scheduler(
        courses=[shared],          # the SAME course object only once
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )

    # Act
    schedules = scheduler.generateAllSchedules()
    # Assert — every schedule has exactly one assignment whose course
    # is the shared course.
    assert len(schedules) > 0
    for s in schedules:
        shared_assignments = [
            a for a in s.assignments if a.course.courseId == "10101"
        ]
        assert len(shared_assignments) == 1


# ---------------------------------------------------------------------------
# TC-ENG-007 — Only EXAM courses are scheduled.
# ---------------------------------------------------------------------------


# TC-ENG-007: Check that courses like projects or attendance-only are ignored 
# by the scheduler.
def test_only_exam_courses_are_scheduled(
    make_course, make_program_entry, make_period,
):
    # Arrange — mix of EXAM, PROJECT, ATTENDANCE.
    pe = make_program_entry(program_id="83101", year=2)
    exam_course = make_course(
        course_id="E", evaluation=EvalType.EXAM, program_entries=[pe])
    project_course = make_course(
        course_id="P", evaluation=EvalType.PROJECT, program_entries=[pe])
    att_course = make_course(
        course_id="A", evaluation=EvalType.ATTENDANCE, program_entries=[pe])
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 3), excluded=[]
    )
    scheduler = Scheduler(
        courses=[exam_course, project_course, att_course],
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )
    # Act
    schedules = scheduler.generateAllSchedules()
    # Assert — only the EXAM course appears in any schedule.
    assert len(schedules) > 0
    for s in schedules:
        ids = {a.course.courseId for a in s.assignments}
        assert ids == {"E"}

    
# ---------------------------------------------------------------------------
# TC-ENG-008 — Program with no EXAM courses returns empty schedule.
# ---------------------------------------------------------------------------

# If a study program only has 'Project' or 'Attendance' courses 
# (and zero 'Exam' courses), the system should just return an empty 
# schedule. It must not crash.
def test_program_with_only_non_exam_courses_returns_empty_schedule(
    make_course, make_program_entry, make_period,
):
    # Arrange — Create a program that only has a project and attendance.
    pe = make_program_entry(program_id="83101", year=2)
    project_course = make_course(
        course_id="P1", evaluation=EvalType.PROJECT, program_entries=[pe])
    att_course = make_course(
        course_id="A1", evaluation=EvalType.ATTENDANCE, program_entries=[pe])
    period = make_period(
        start=date(2026, 6, 1), end=date(2026, 6, 5), excluded=[]
    )

    scheduler = Scheduler(
        courses=[project_course, att_course],
        periods=[period],
        conflictCheckers=_default_checkers([period]),
        validators=[],
    )

    # Act — Run the scheduler. It should not cause any errors.
    schedules = scheduler.generateAllSchedules()

    # Assert — Check that there are no exams inside the created schedules.
    if len(schedules) > 0:
        for s in schedules:
            assert len(s.assignments) == 0, (
                "A program with no 'Exam' courses should not create "
                "any exam schedules."
            )