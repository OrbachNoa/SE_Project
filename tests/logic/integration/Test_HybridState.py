"""Integration tests for HybridScheduleResultState's SQLite-backed paging.

Unlike the in-memory ScheduleResultState, this state keeps only the
currently visible window of schedules in memory and delegates counting,
windowing, and clearing to a repository (mocked here). Tests cover
construction defaults, count/sqlite_count delegation, the
is_first_window_ready readiness check, total_pages' ceiling-division
arithmetic across boundary values, load_page's window-fetch and index
reset, its bounds-checking, set_schedules' reset-and-clear, and
add_schedules_batch's fetch-only-when-under-capacity behaviour.

Conventions:
- Each test carries a unique TC-HYB-STA-NNN identifier in the comment
  block above its definition, numbered sequentially.
- Each test body is split into Arrange / Act / Assert sections. The
  Act/Assert merge into one block only where the assertion is itself a
  `pytest.raises` context manager — plain return-value checks keep
  separate Act and Assert sections.
- `mock_repository` and `make_schedule_dto` come from the shared fixtures
  in tests/conftest.py.
"""
import pytest
from src.application.state.HybridScheduleResultState import HybridScheduleResultState

# ===========================================================================
# TC-HYB-STA-001: construction must set current_page/current_index to 0
# and store the repository and window_size exactly as given.
# ===========================================================================
def test_hybrid_state_initialization(mock_repository):
    # Act
    state = HybridScheduleResultState(mock_repository, window_size=10)

    # Assert
    assert state.current_page == 0
    assert state.current_index == 0
    assert state._repository == mock_repository
    assert state._window_size == 10

# ===========================================================================
# TC-HYB-STA-002: count() and sqlite_count() must both delegate to the
# repository's count() — they report the same underlying number, not two
# independently tracked counters that could drift apart.
# ===========================================================================
def test_hybrid_state_count(mock_repository):
    # Arrange
    mock_repository.count.return_value = 42
    state = HybridScheduleResultState(mock_repository, window_size=10)

    # Act
    count_result = state.count()
    sqlite_count_result = state.sqlite_count()

    # Assert
    assert count_result == 42
    assert sqlite_count_result == 42
    mock_repository.count.assert_called()

# ===========================================================================
# TC-HYB-STA-003: is_first_window_ready() must track the repository's
# count directly — false while empty, true as soon as any row exists.
# ===========================================================================
def test_hybrid_state_is_first_window_ready(mock_repository):
    # Arrange
    state = HybridScheduleResultState(mock_repository, window_size=10)

    # Act
    mock_repository.count.return_value = 0
    ready_when_empty = state.is_first_window_ready()
    mock_repository.count.return_value = 5
    ready_when_populated = state.is_first_window_ready()

    # Assert
    assert ready_when_empty is False
    assert ready_when_populated is True

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
# TC-HYB-STA-005: Verify load_page updates current page without fetching the full window.
# ===========================================================================
def test_hybrid_state_load_page(mock_repository, make_schedule_dto):
    # Arrange
    mock_repository.count.return_value = 25
    mock_repository.get_raw_by_ids.return_value = ({}, {}, [])
    state = HybridScheduleResultState(mock_repository, window_size=10)
    state._current_index = 3 
    
    # Act
    state.load_page(1)
    
    # Assert
    assert state.current_page == 1
    assert state.current_index == 0
    mock_repository.get_window_raw.assert_not_called()
    mock_repository.get_raw_by_ids.assert_called_once_with([])
    assert state.current_window_size() == 10

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
# TC-HYB-STA-008: Verify add_schedules_batch does not reload the SQLite window.
# ===========================================================================
def test_hybrid_state_add_schedules_batch_does_not_fetch_window(mock_repository, make_schedule_dto):
    # Arrange
    mock_repository.count.return_value = 18
    state = HybridScheduleResultState(mock_repository, window_size=10)
    state._schedules = [make_schedule_dto() for _ in range(5)] 
    state._current_page_idx = 1

    # Act
    state.add_schedules_batch(3)
    
    # Assert
    mock_repository.get_window_raw.assert_not_called()
    assert state.current_window_size() == 8

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
    mock_repository.get_window_raw.assert_not_called()
