"""
conftest.py — Shared tools (fixtures) for the exam scheduling tests.

This file creates basic objects like Courses and Dates. This makes it easier 
to write tests because you only change the specific parts you need to check.
"""
# region Imports
from datetime import date
from pathlib import Path
import sys
from unittest.mock import MagicMock
import pytest
from src.models.Enums import EvalType, Semester, Moed, Requirement
from src.models.Domain import (
    Course,
    ProgramEntry,
    ExamPeriod,
    ExamAssignment,
    ExamSchedule,
)
from src.infrastructure.repositories.SQLiteScheduleRepository import SQLiteScheduleRepository
# endregion

# region Path Setup
# Add 'src' and project root to sys.path so pytest can resolve absolute imports inside the src directory.
SRC_ROOT = Path(__file__).resolve().parent.parent / "src"
PROJECT_ROOT = SRC_ROOT.parent
for path in (str(SRC_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)
# endregion


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


@pytest.fixture
def collector_observer():
    """Provides a fresh observer to collect schedules in test cases."""
    # to be implemented under src by someone else
    pass


@pytest.fixture(scope="session")
def qapp():
    """Ensures a single QApplication instance exists for all PyQt tests."""
    from PyQt6.QtWidgets import QApplication
    import sys
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def make_assignment_dto(make_assignment):
    """Provides a factory to build AssignmentDTOs with default values matched to the domain fixtures."""
    from src.application.dto.ScheduleDTO import AssignmentDTO
    def _make(
        course_id=None,
        course_name=None,
        instructor=None,
        date=None,
        semester=None,
        moed=None
    ):
        domain_a = make_assignment()
        return AssignmentDTO(
            course_id=course_id or domain_a.course.courseId,
            course_name=course_name or domain_a.course.name,
            instructor=instructor or domain_a.course.instructor,
            date=date or domain_a.date.isoformat(),
            semester=semester or (domain_a.semester.value if hasattr(domain_a.semester, 'value') else domain_a.semester),
            moed=moed or (domain_a.moed.value if hasattr(domain_a.moed, 'value') else domain_a.moed)
        )
    return _make


@pytest.fixture
def make_schedule_dto(make_assignment_dto):
    """Provides a factory to build ScheduleDTOs with default values."""
    from src.application.dto.ScheduleDTO import ScheduleDTO
    def _make(assignments=None, total_assignments=None):
        if assignments is None:
            assignments = []
        if total_assignments is None:
            total_assignments = len(assignments)
        return ScheduleDTO(assignments=assignments, total_assignments=total_assignments)
    return _make


@pytest.fixture
def make_data_cache(make_course, make_period):
    """Provides a factory to build DataCaches with default values matched to domain fixtures."""
    from src.infrastructure.cache.DataCache import DataCache
    def _make(courses=None, periods=None, source_hashes=None):
        if courses is None:
            c = make_course()
            courses = [{
                "courseId": c.courseId,
                "name": c.name,
                "instructor": c.instructor,
                "evaluation": c.evaluation.value if hasattr(c.evaluation, 'value') else c.evaluation,
                "programEntries": [{
                    "programId": pe.programId,
                    "year": pe.year,
                    "semester": pe.semester.value if hasattr(pe.semester, 'value') else pe.semester,
                    "requirement": pe.requirement.value if hasattr(pe.requirement, 'value') else pe.requirement
                } for pe in c.programEntries]
            }]
        if periods is None:
            p = make_period(
                start=date(2026, 6, 1),
                end=date(2026, 6, 3),
                excluded=[date(2026, 6, 2)]
            )
            periods = [{
                "semester": p.semester.value if hasattr(p.semester, 'value') else p.semester,
                "moed": p.moed.value if hasattr(p.moed, 'value') else p.moed,
                "startDate": p.startDate.isoformat(),
                "endDate": p.endDate.isoformat(),
                "excludedDates": [d.isoformat() for d in p.excludedDates]
            }]
        return DataCache(
            courses=courses,
            periods=periods,
            source_hashes=source_hashes or {}
        )
    return _make

@pytest.fixture
def mock_repository():
    """Provides a MagicMock spec'd for SQLiteScheduleRepository to isolate tests from disk I/O."""
    return MagicMock(spec=SQLiteScheduleRepository)


@pytest.fixture
def mock_controller():
    """Provides a mocked AppController with standard PyQt signals and stubbed methods."""
    controller = MagicMock()
    # Mock PyQt signals on controller
    controller.schedule_found = MagicMock()
    controller.progress_updated = MagicMock()
    controller.search_finished = MagicMock()
    controller.error_occurred = MagicMock()
    controller.early_results_ready = MagicMock()
    controller.total_count_updated = MagicMock()
    controller.get_page_info.return_value = {
        "current_page": 0,
        "total_pages": 1,
        "total_count": 0,
        "window_size": 0,
        "sqlite_count": 0,
    }
    return controller


@pytest.fixture
def mock_router():
    """Provides a MagicMock for the screen router."""
    return MagicMock()


@pytest.fixture
def viewmodel_mapper():
    """Provides a fresh ViewModelMapper instance."""
    from src.application.services.ViewModelMapper import ViewModelMapper
    return ViewModelMapper()


@pytest.fixture
def app_state():
    """Provides a fresh AppState instance."""
    from src.application.state.AppState import AppState
    return AppState()



