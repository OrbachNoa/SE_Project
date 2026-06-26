"""Integration tests for InputDataState and ScheduleResultState.

InputDataState holds the loaded courses/periods in memory and can
serialize them to/from a DataCache for persistence between runs.
ScheduleResultState holds the generated schedule results and tracks which
one is currently selected. Tests cover mutation, the empty-state defaults,
the DataCache round trip in both directions, and index bounds-checking on
both the schedule list and the current-index setter.

Conventions:
- Each test carries a unique TC-AS-NNN identifier in the comment block
  above its definition, numbered sequentially. TC-AS-001 does not exist in
  this file — left as a gap rather than renumbering the rest, to avoid
  breaking traceability for no functional gain.
- Each test body is split into Arrange / Act / Assert sections, except
  where the assertion is itself the pytest.raises context manager.
- `make_course`, `make_period`, `make_schedule_dto`, and `make_data_cache`
  come from the shared fixtures in tests/conftest.py.
"""
import pytest
from datetime import date
from src.models.Enums import EvalType, Semester, Moed, Requirement
from src.infrastructure.cache.DataCache import DataCache
from src.application.state.InputDataState import InputDataState
from src.application.state.ScheduleResultState import ScheduleResultState

# ===========================================================================
# TC-AS-002: replace_courses/replace_periods must overwrite the state's
# lists, and the getters must return exactly what was just set.
# ===========================================================================
def test_input_data_state_mutators(make_course, make_period):
    # Arrange
    state = InputDataState()
    c1 = make_course(course_id="10101")
    c2 = make_course(course_id="10102")
    p1 = make_period(semester=Semester.FALL)
    
    # Act
    state.replace_courses([c1, c2])
    state.replace_periods([p1])
    
    # Assert
    assert state.get_courses() == [c1, c2]
    assert state.get_periods() == [p1]


# ===========================================================================
# TC-AS-003: a freshly constructed InputDataState must start with empty
# course/period lists, not None or uninitialised attributes.
# ===========================================================================
def test_input_data_state_initial_empty():
    # Act
    state = InputDataState()

    # Assert
    assert state.get_courses() == []
    assert state.get_periods() == []


# ===========================================================================
# TC-AS-004: to_cache() must serialize the loaded courses/periods into the
# plain-dict shape DataCache expects, preserving nested fields like
# program entries and excluded dates.
# ===========================================================================
def test_input_data_state_to_cache(make_course, make_period):
    # Arrange
    state = InputDataState()
    course = make_course(course_id="10101")
    period = make_period(
        semester=Semester.FALL,
        moed=Moed.ALEPH,
        start=date(2026, 6, 1),
        end=date(2026, 6, 3),
        excluded=[date(2026, 6, 2)]
    )
    state.replace_courses([course])
    state.replace_periods([period])
    
    # Act
    cache = state.to_cache()
    
    # Assert
    assert isinstance(cache, DataCache)
    assert len(cache.courses) == 1
    assert cache.courses[0]["courseId"] == "10101"
    assert cache.courses[0]["programEntries"][0]["programId"] == "83101"
    assert len(cache.periods) == 1
    assert cache.periods[0]["startDate"] == "2026-06-01"
    assert cache.periods[0]["excludedDates"] == ["2026-06-02"]


# ===========================================================================
# TC-AS-005: load_cache() must rebuild real domain objects (Course,
# ExamPeriod) from a DataCache's plain dicts — the reverse of to_cache(),
# restoring enum values and date types correctly, not just raw strings.
# ===========================================================================
def test_input_data_state_load_cache(make_data_cache):
    # Arrange
    state = InputDataState()
    cache = make_data_cache()
    
    # Act
    state.load_cache(cache)
    
    # Assert 
    # courses assert
    rebuilt_courses = state.get_courses()
    assert len(rebuilt_courses) == 1
    c = rebuilt_courses[0]
    assert c.courseId == "10101"
    assert c.evaluation == EvalType.EXAM
    assert c.programEntries[0].programId == "83101"
    assert c.programEntries[0].semester == Semester.FALL
    
    # periods assert
    rebuilt_periods = state.get_periods()
    assert len(rebuilt_periods) == 1
    p = rebuilt_periods[0]
    assert p.semester == Semester.FALL
    assert p.moed == Moed.ALEPH
    assert p.startDate == date(2026, 6, 1)
    assert p.excludedDates == {date(2026, 6, 2)}


# ===========================================================================
# TC-AS-006: a freshly constructed ScheduleResultState must report zero
# schedules — there is no implicit pre-populated result set.
# ===========================================================================
def test_schedule_result_state_initial_empty():
    # Act
    state = ScheduleResultState()

    # Assert
    assert state.count() == 0


# ===========================================================================
# TC-AS-007: set_schedules() must replace the entire list — count() and
# get_schedule() must reflect the new list, not append to a prior one.
# ===========================================================================
def test_schedule_result_state_set_schedules(make_schedule_dto):
    # Arrange
    state = ScheduleResultState()
    dto1 = make_schedule_dto()
    
    # Act
    state.set_schedules([dto1])
    
    # Assert
    assert state.count() == 1
    assert state.get_schedule(0) == dto1


# ===========================================================================
# TC-AS-008: add_schedule() must append, preserving the existing entries
# and their original order — not replace or shuffle the list.
# ===========================================================================
def test_schedule_result_state_add_schedule(make_schedule_dto):
    # Arrange
    state = ScheduleResultState()
    dto1 = make_schedule_dto()
    dto2 = make_schedule_dto()
    state.set_schedules([dto1])
    
    # Act
    state.add_schedule(dto2)
    
    # Assert
    assert state.count() == 2
    assert state.get_schedule(0) == dto1
    assert state.get_schedule(1) == dto2


# ===========================================================================
# TC-AS-009: get_schedule() must raise IndexError for both a negative
# index and an index past the end, not silently clamp or wrap around.
# ===========================================================================
@pytest.mark.parametrize("bad_index", [-1, 2])
def test_schedule_result_state_get_schedule_index_error(bad_index, make_schedule_dto):
    # Arrange
    state = ScheduleResultState()
    dto = make_schedule_dto()
    state.set_schedules([dto, dto])
    
    # Act & Assert
    with pytest.raises(IndexError):
        state.get_schedule(bad_index)


# ===========================================================================
# TC-AS-010: a freshly constructed ScheduleResultState must start at
# current_index 0 — the first result, not an uninitialised value.
# ===========================================================================
def test_schedule_result_state_initial_index():
    # Act
    state = ScheduleResultState()

    # Assert
    assert state.current_index == 0


# ===========================================================================
# TC-AS-011: setting current_index to any in-bounds value (start, middle,
# end) must succeed and be reflected immediately.
# ===========================================================================
@pytest.mark.parametrize("valid_index", [0, 1, 2])
def test_schedule_result_state_current_index_updates(valid_index, make_schedule_dto):
    # Arrange
    state = ScheduleResultState()
    dto = make_schedule_dto()
    state.set_schedules([dto, dto, dto])
    
    # Act
    state.current_index = valid_index
    
    # Assert
    assert state.current_index == valid_index


# ===========================================================================
# TC-AS-012: setting current_index to an out-of-bounds value (negative or
# past the end) must raise IndexError, mirroring get_schedule()'s guard.
# ===========================================================================
@pytest.mark.parametrize("bad_index", [-1, 3])
def test_schedule_result_state_current_index_out_of_bounds(bad_index, make_schedule_dto):
    # Arrange
    state = ScheduleResultState()
    dto = make_schedule_dto()
    state.set_schedules([dto, dto, dto])
    
    # Act & Assert
    with pytest.raises(IndexError):
        state.current_index = bad_index
