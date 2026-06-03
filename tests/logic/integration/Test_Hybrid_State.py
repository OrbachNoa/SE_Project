import pytest
from src.application.HybridScheduleResultState import HybridScheduleResultState

# ===========================================================================
# TC-HYB-STA-001: Verify that HybridScheduleResultState initializes correctly.
# ===========================================================================
def test_hybrid_state_initialization(mock_repository):
    # Arrange & Act
    state = HybridScheduleResultState(mock_repository, window_size=10)
    
    # Assert
    assert state.current_page == 0
    assert state.current_index == 0
    assert state._repository == mock_repository
    assert state._window_size == 10

# ===========================================================================
# TC-HYB-STA-002: Verify that count methods delegate to the repository.
# ===========================================================================
def test_hybrid_state_count(mock_repository):
    # Arrange
    mock_repository.count.return_value = 42
    state = HybridScheduleResultState(mock_repository, window_size=10)
    
    # Act & Assert
    assert state.count() == 42
    assert state.sqlite_count() == 42
    mock_repository.count.assert_called()

# ===========================================================================
# TC-HYB-STA-003: Verify is_first_window_ready returns True if repository is not empty.
# ===========================================================================
def test_hybrid_state_is_first_window_ready(mock_repository):
    # Arrange
    state = HybridScheduleResultState(mock_repository, window_size=10)
    
    # Act & Assert
    mock_repository.count.return_value = 0
    assert not state.is_first_window_ready()
    
    mock_repository.count.return_value = 5
    assert state.is_first_window_ready()

# ===========================================================================
# TC-HYB-STA-004: Verify total_pages computes the ceiling of pages correctly.
# ===========================================================================
@pytest.mark.parametrize("total_count,window_size,expected_pages", [
    (0, 10, 0),
    (5, 10, 1),
    (10, 10, 1),
    (11, 10, 2),
    (25, 10, 3),
])
def test_hybrid_state_total_pages(total_count, window_size, expected_pages, mock_repository):
    # Arrange
    mock_repository.count.return_value = total_count
    state = HybridScheduleResultState(mock_repository, window_size=window_size)
    
    # Act & Assert
    assert state.total_pages() == expected_pages

# ===========================================================================
# TC-HYB-STA-005: Verify load_page updates current page, queries window and resets current index.
# ===========================================================================
def test_hybrid_state_load_page(mock_repository, make_schedule_dto):
    # Arrange
    mock_repository.count.return_value = 25
    state = HybridScheduleResultState(mock_repository, window_size=10)
    
    dummy_dtos = [make_schedule_dto() for _ in range(5)]
    mock_repository.get_window.return_value = dummy_dtos
    state._current_index = 3 
    
    # Act
    state.load_page(1)
    
    # Assert
    assert state.current_page == 1
    assert state.current_index == 0
    mock_repository.get_window.assert_called_once_with(10, 10)
    assert state.current_window_size() == 5

# ===========================================================================
# TC-HYB-STA-006: Verify load_page raises IndexError for invalid page bounds.
# ===========================================================================
@pytest.mark.parametrize("bad_page", [-1, 3])
def test_hybrid_state_load_page_index_error(bad_page, mock_repository):
    # Arrange
    mock_repository.count.return_value = 25  # 3 pages: 0, 1, 2
    state = HybridScheduleResultState(mock_repository, window_size=10)
    
    # Act & Assert
    with pytest.raises(IndexError):
        state.load_page(bad_page)

# ===========================================================================
# TC-HYB-STA-007: Verify set_schedules clears repository and resets current page.
# ===========================================================================
def test_hybrid_state_set_schedules(mock_repository):
    # Arrange
    state = HybridScheduleResultState(mock_repository, window_size=10)
    state._current_page_idx = 2
    
    # Act
    state.set_schedules([])
    
    # Assert
    assert state.current_page == 0
    mock_repository.clear.assert_called_once()

# ===========================================================================
# TC-HYB-STA-008: Verify add_schedules_batch fetches new window if below capacity.
# ===========================================================================
def test_hybrid_state_add_schedules_batch_under_capacity(mock_repository, make_schedule_dto):
    # Arrange
    state = HybridScheduleResultState(mock_repository, window_size=10)
    state._schedules = [make_schedule_dto() for _ in range(5)] 
    state._current_page_idx = 1
    
    dummy_dtos = [make_schedule_dto() for _ in range(8)]
    mock_repository.get_window.return_value = dummy_dtos
    
    # Act
    state.add_schedules_batch(3)
    
    # Assert
    mock_repository.get_window.assert_called_once_with(10, 10)
    assert len(state._schedules) == 8

# ===========================================================================
# TC-HYB-STA-009: Verify add_schedules_batch does not fetch if at capacity.
# ===========================================================================
def test_hybrid_state_add_schedules_batch_at_capacity(mock_repository, make_schedule_dto):
    # Arrange
    state = HybridScheduleResultState(mock_repository, window_size=10)
    state._schedules = [make_schedule_dto() for _ in range(10)] 
    
    # Act
    state.add_schedules_batch(5)
    
    # Assert
    mock_repository.get_window.assert_not_called()