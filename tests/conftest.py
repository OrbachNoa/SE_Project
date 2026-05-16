"""
conftest.py — Shared tools (fixtures) for the exam scheduling tests.

This file creates basic objects like Courses and Dates. This makes it easier 
to write tests because you only change the specific parts you need to check.
"""
from datetime import date
import pytest

# ---------------------------------------------------------------------------
# Imports for the system
# ---------------------------------------------------------------------------
from src.models.enums import EvalType, Semester, Moed, Requirement
from src.models.domain import (
    Course,
    ProgramEntry,
    ExamPeriod,
    ExamAssignment,
    ExamSchedule,
)


# ---------------------------------------------------------------------------
# Factory fixtures — These functions build objects with basic "default" values.
# ---------------------------------------------------------------------------

@pytest.fixture
def make_program_entry():
    """
    Creates a basic Program Entry. 
    Default: Program 83101, Year 2, Fall, Mandatory.
    """
    def _make(program_id="83101", year=2,
              semester=Semester.FALL,
              requirement=Requirement.OBLIGATORY):
        return ProgramEntry(
            program_id=program_id,
            year=year,
            semester=semester,
            requirement=requirement,
        )
    return _make


@pytest.fixture
def make_course(make_program_entry):
    """
    Creates a basic Course. 
    Default: A mandatory exam in program 83101.
    """
    def _make(course_id="10101", name="Calculus 1",
              instructor="Dr. Cohen",
              evaluation=EvalType.EXAM,
              program_entries=None):
        if program_entries is None:
            program_entries = [make_program_entry()]
        return Course(
            course_id=course_id,
            name=name,
            instructor=instructor,
            evaluation=evaluation,
            program_entries=program_entries,
        )
    return _make


@pytest.fixture
def make_period():
    """
    Creates a basic Exam Period (the dates for the exams).
    Default: June 1, 2026 to June 30, 2026.
    """
    def _make(semester=Semester.FALL, moed=Moed.ALEPH,
              start=date(2026, 6, 1), end=date(2026, 6, 30),
              excluded=None):
        return ExamPeriod(
            semester=semester,
            moed=moed,
            start_date=start,
            end_date=end,
            excluded_dates=excluded or [],
        )
    return _make


@pytest.fixture
def make_assignment(make_course):
    """
    Creates a basic Exam Assignment (matching a course to a date).
    Default: A course on June 5, 2026.
    """
    def _make(course=None, exam_date=date(2026, 6, 5), moed=Moed.ALEPH):
        if course is None:
            course = make_course()
        sem = course.programEntries[0].semester if course.programEntries else Semester.FALL
        assignment = ExamAssignment(course=course, date=exam_date, moed=moed, semester=sem)
        return assignment
    return _make


@pytest.fixture
def empty_schedule():
    """Returns a new schedule with zero exams, used to start tests."""
    return ExamSchedule()