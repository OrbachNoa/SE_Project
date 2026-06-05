import pytest
from datetime import date
from src.models.Enums import EvalType, Semester, Moed, Requirement
from src.infrastructure.cache.DataCache import DataCache
from src.application.state.AppState import AppState
from src.application.state.InputDataState import InputDataState
from src.application.state.ScheduleResultState import ScheduleResultState

# ===========================================================================
# TC-AS-001: Verify that AppState sets up InputDataState and ScheduleResultState.
# ===========================================================================
def test_app_state_initialization():
    # Arrange & Act
    state = AppState()
    
    # Assert
    assert isinstance(state.get_input_state(), InputDataState)
    assert isinstance(state.get_schedule_state(), ScheduleResultState)

# ===========================================================================
# TC-AS-002: Test that InputDataState mutators replace and retrieve courses and periods.
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
# TC-AS-003: Test that InputDataState starts with empty lists.
# ===========================================================================
def test_input_data_state_initial_empty():
    # Arrange & Act
    state = InputDataState()
    
    # Assert
    assert state.get_courses() == []
    assert state.get_periods() == []


# ===========================================================================
# TC-AS-004: Test that InputDataState serializes domain models to DataCache correctly.
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
# TC-AS-005: Test that InputDataState deserializes DataCache to domain models correctly.
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
# TC-AS-006: Test that ScheduleResultState initializes empty.
# ===========================================================================
def test_schedule_result_state_initial_empty():
    # Arrange & Act
    state = ScheduleResultState()
    
    # Assert
    assert state.count() == 0


# ===========================================================================
# TC-AS-007: Test that set_schedules overwrites schedule list in ScheduleResultState.
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
# TC-AS-008: Test that add_schedule appends to the schedule list.
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
# TC-AS-009: Test that get_schedule raises IndexError for invalid index values.
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
# TC-AS-010: Test that ScheduleResultState initializes with current_index of 0.
# ===========================================================================
def test_schedule_result_state_initial_index():
    # Arrange & Act
    state = ScheduleResultState()
    
    # Assert
    assert state.current_index == 0


# ===========================================================================
# TC-AS-011: Test that current_index setter updates index within valid bounds.
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
# TC-AS-012: Test that current_index setter raises IndexError for out-of-bound values.
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
