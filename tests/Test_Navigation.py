import pytest
from src.application.schedule_result_state import ScheduleResultState
from src.application.view_model_mapper import ViewModelMapper


# ===========================================================================
# TC-NAV-001: Verify that ScheduleResultState raises IndexError if index is updated when count is 0.
# ===========================================================================
def test_navigation_empty_state_raises_index_error():
    # Arrange
    state = ScheduleResultState()
    
    # Act & Assert
    with pytest.raises(IndexError):
        state.current_index = 0


# ===========================================================================
# TC-NAV-002: Verify that setting schedules resets current index to 0.
# ===========================================================================
def test_navigation_set_schedules_defaults_to_zero(make_schedule_dto):
    # Arrange
    state = ScheduleResultState()
    dto = make_schedule_dto()
    
    # Act
    state.set_schedules([dto, dto, dto])
    
    # Assert
    assert state.count() == 3
    assert state.current_index == 0


# ===========================================================================
# TC-NAV-003: Verify that current_index can be updated to valid indices.
# ===========================================================================
@pytest.mark.parametrize("valid_index", [0, 1, 2])
def test_navigation_valid_index_updates(valid_index, make_schedule_dto):
    # Arrange
    state = ScheduleResultState()
    dto = make_schedule_dto()
    state.set_schedules([dto, dto, dto])
    
    # Act
    state.current_index = valid_index
    
    # Assert
    assert state.current_index == valid_index


# ===========================================================================
# TC-NAV-004: Verify that current_index raises IndexError for out-of-bounds inputs.
# ===========================================================================
@pytest.mark.parametrize("bad_index", [-1, 3])
def test_navigation_index_out_of_bounds_errors(bad_index, make_schedule_dto):
    # Arrange
    state = ScheduleResultState()
    dto = make_schedule_dto()
    state.set_schedules([dto, dto, dto])
    
    # Act & Assert
    with pytest.raises(IndexError):
        state.current_index = bad_index


# ===========================================================================
# TC-NAV-005: Verify that setting new schedules resets current index to 0.
# ===========================================================================
def test_navigation_reset_on_set_schedules(make_schedule_dto):
    # Arrange
    state = ScheduleResultState()
    dto = make_schedule_dto()
    state.set_schedules([dto, dto, dto])
    state.current_index = 2
    
    # Act
    state.set_schedules([dto, dto])
    
    # Assert
    assert state.current_index == 0


# ===========================================================================
# TC-NAV-006: Verify that ViewModelMapper maps the navigation context for empty schedules correctly.
# ===========================================================================
def test_viewmodel_navigation_context_mapping_empty(make_schedule_dto):
    # Arrange
    mapper = ViewModelMapper()
    dto = make_schedule_dto()
    
    # Act
    vm = mapper.to_schedule_vm(dto, current_index=2, total=5)
    
    # Assert
    assert vm.current_index == 2
    assert vm.total == 5
    assert vm.is_empty() is True


# ===========================================================================
# TC-NAV-007: Verify that ViewModelMapper maps the navigation context and items for non-empty schedules correctly.
# ===========================================================================
def test_viewmodel_navigation_context_mapping_non_empty(make_assignment_dto, make_schedule_dto):
    # Arrange
    mapper = ViewModelMapper()
    a = make_assignment_dto()
    dto_with_items = make_schedule_dto(assignments=[a], total_assignments=1)
    
    # Act
    vm_with_items = mapper.to_schedule_vm(dto_with_items, current_index=0, total=1)
    
    # Assert
    assert vm_with_items.current_index == 0
    assert vm_with_items.total == 1
    assert vm_with_items.is_empty() is False
    assert len(vm_with_items.items) == 1
    assert vm_with_items.items[0].date == "2026-06-05"
