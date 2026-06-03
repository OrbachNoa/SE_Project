from datetime import date
from unittest.mock import MagicMock
import pytest

from src.models.enums import EvalType, Semester, Moed, Requirement
from src.logic.ProgramYearConflictChecker import ProgramYearConflictChecker
from src.logic.MoedOrderChecker import MoedOrderChecker
from src.logic.Scheduler import Scheduler
from src.logic.SlotBuilder import SlotBuilder
from src.logic.CollectingScheduleObserver import CollectingScheduleObserver


# Helper: Creates the default checkers and gives them the exam dates they need.
def _default_checkers(periods, courses):
    py_checker = ProgramYearConflictChecker()
    py_checker.precompute_conflicts(courses)
    return [
        py_checker,
        MoedOrderChecker()
    ]


# ===========================================================================
# TC-ENG-001: Test that simple input creates the correct number of schedules.
# Two OBLIGATORY courses, same program/year, with three
# available dates — every pair of distinct dates is a valid schedule.
# ===========================================================================
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

    slots = SlotBuilder([period]).build([c1, c2])
    scheduler = Scheduler(_default_checkers([period], [c1, c2]))
    observer = CollectingScheduleObserver()
    # Act - pass the observer to the scheduler instead of UI logic
    scheduler.generateSchedules(slots, observer)
    schedules = observer.schedules
    # Assert - expect 6 different valid schedules
    assert len(schedules) == 6


# ===========================================================================
# TC-ENG-002: Test that the system returns more than one schedule.
# When there are many days and no conflicts, the system should find multiple valid schedules.
# ===========================================================================
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
    slots = SlotBuilder([period]).build(courses)
    scheduler = Scheduler(_default_checkers([period], courses))
    observer = CollectingScheduleObserver()
    # Act - pass the observer to the scheduler instead of UI logic
    scheduler.generateSchedules(slots, observer)
    schedules = observer.schedules
    # Assert - expect more than 1 valid schedule
    assert len(schedules) > 1


# ===========================================================================
# TC-ENG-003: Test that the system returns an empty list if no schedule is possible.
# If two mandatory courses must be on the same day, they conflict.
# The system should return an empty list instead of crashing.
# ===========================================================================
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
    slots = SlotBuilder([period]).build([c1, c2])
    scheduler = Scheduler(_default_checkers([period], [c1, c2]))
    observer = CollectingScheduleObserver()
    # Act - pass the observer to the scheduler instead of UI logic
    scheduler.generateSchedules(slots, observer)
    schedules = observer.schedules
    # Assert - expect an empty list instead of crashing
    assert schedules == []


# ===========================================================================
# TC-ENG-004: Test that every schedule has all the required courses.
# With four EXAM courses and six available dates, every
# returned schedule must contain exactly four assignments.
# ===========================================================================
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
    slots = SlotBuilder([period]).build(courses)
    scheduler = Scheduler(_default_checkers([period], courses))
    observer = CollectingScheduleObserver()
    # Act - pass the observer to the scheduler instead of UI logic
    scheduler.generateSchedules(slots, observer)
    schedules = observer.schedules
    # Assert 
    # - expect more than 0 valid schedules
    # - expect every schedule to have exactly 4 assignments
    assert len(schedules) > 0
    assert all(len(s.assignments) == 4 for s in schedules)


# ===========================================================================
# TC-ENG-005: Test that we can add a new type of conflict checker easily.
# We can give the system a custom checker, and the system should use it to find conflicts.
# ===========================================================================
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

    slots = SlotBuilder([period]).build(courses)
    scheduler = Scheduler([rejector])
    observer = CollectingScheduleObserver()
    # Act - pass the observer to the scheduler instead of UI logic
    scheduler.generateSchedules(slots, observer)
    schedules = observer.schedules
    # Assert 
    # - expect an empty list instead of crashing
    # - expect the custom checker to be called
    assert schedules == []
    assert rejector.calls > 0


# ===========================================================================
# TC-ENG-006: Courses shared across programs scheduled exactly once.
# If a course is part of two different study programs, it should
# only appear once in the final schedule.
# ===========================================================================
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
    slots = SlotBuilder([period]).build([shared])
    scheduler = Scheduler(_default_checkers([period], [shared]))
    observer = CollectingScheduleObserver()
    # Act - pass the observer to the scheduler instead of UI logic
    scheduler.generateSchedules(slots, observer)
    schedules = observer.schedules
    # Assert 
    # - expect more than 0 valid schedules
    # - expect every schedule to have exactly one assignment whose course is the shared course
    assert len(schedules) > 0
    for s in schedules:
        shared_assignments = [
            a for a in s.assignments if a.course.courseId == "10101"
        ]
        assert len(shared_assignments) == 1


# ===========================================================================
# TC-ENG-007: Only EXAM courses are scheduled.
# Check that courses like projects or attendance-only are ignored 
# by the scheduler.
# ===========================================================================
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
    courses = [exam_course, project_course, att_course]
    slots = SlotBuilder([period]).build(courses)
    scheduler = Scheduler(_default_checkers([period], courses))
    observer = CollectingScheduleObserver()
    # Act - pass the observer to the scheduler instead of UI logic
    scheduler.generateSchedules(slots, observer)
    schedules = observer.schedules
    # Assert 
    # - expect more than 0 valid schedules
    # - expect only the EXAM course to appear in any schedule
    assert len(schedules) > 0
    for s in schedules:
        ids = {a.course.courseId for a in s.assignments}
        assert ids == {"E"}


# ===========================================================================
# TC-ENG-008: Program with no EXAM courses returns empty schedule.
# If a study program only has 'Project' or 'Attendance' courses, 
# the system should just return an empty schedule.
# ===========================================================================
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

    courses = [project_course, att_course]
    slots = SlotBuilder([period]).build(courses)
    scheduler = Scheduler(_default_checkers([period], courses))
    observer = CollectingScheduleObserver()
    # Act - pass the observer to the scheduler instead of UI logic
    scheduler.generateSchedules(slots, observer)
    schedules = observer.schedules
    # Assert 
    # - expect more than 0 valid schedules
    # - expect only the EXAM course to appear in any schedule
    if len(schedules) > 0:
        for s in schedules:
            assert len(s.assignments) == 0, (
                "A program with no 'Exam' courses should not create "
                "any exam schedules."
            )
