"""
Test suite for SolutionPagingPresenter.

Scope   : Verifies pagination logic (page counts, boundaries, solution indexing).
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-PAG-001..003
"""
from unittest.mock import MagicMock
from src.gui.features.output.SolutionPagingPresenter import SolutionPagingPresenter

# TC-GUI-PAG-001
# SolutionPagingPresenter must correctly format page bar based on total pages.
def test_solution_paging_bar_visibility():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    
    presenter = SolutionPagingPresenter(view, controller)
    
    # Act - 1 page total (should hide page bar)
    presenter.total_pages = 1
    presenter.refresh_page_bar()
    
    # Assert
    view.set_page_bar_visible.assert_called_with(False)
    
    # Act - 2 pages total, on first page
    view.reset_mock()
    presenter.window_capacity = 10
    presenter.total_pages = 2
    presenter.current_page = 0
    presenter.sqlite_count = 100  # More than 1 * 10
    presenter.refresh_page_bar()
    
    # Assert
    view.set_page_bar.assert_called_once_with(
        visible=True,
        label="Page 1 / 2",
        can_first=False,
        can_previous=False,
        can_next=True,
        can_last=True
    )


# TC-GUI-PAG-002
# SolutionPagingPresenter must prevent next page navigation if sqlite data isn't ready yet.
def test_solution_paging_waits_for_sqlite():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    
    presenter = SolutionPagingPresenter(view, controller)
    presenter.window_capacity = 10
    presenter.total_pages = 5
    presenter.current_page = 0
    presenter.sqlite_count = 5  # Only 5 rows in DB, but next page needs 10
    
    # Act
    presenter.refresh_page_bar()
    
    # Assert
    view.set_page_bar.assert_called_once_with(
        visible=True,
        label="Page 1 / 5",
        can_first=False,
        can_previous=False,
        can_next=False,  # Blocked because sqlite_count (5) < rows_needed (10)
        can_last=False
    )


# TC-GUI-PAG-003
# SolutionPagingPresenter must limit next/prev solution logic bounds.
def test_solution_paging_solution_boundaries():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    
    presenter = SolutionPagingPresenter(view, controller)
    presenter.show_current = MagicMock()
    presenter.total = 3
    presenter.current_index = 0
    
    # Act / Assert
    # Move previous (at 0) - should not decrement
    presenter.on_prev_solution()
    assert presenter.current_index == 0
    presenter.show_current.assert_not_called()
    
    # Move next (0 to 1)
    presenter.on_next_solution()
    assert presenter.current_index == 1
    presenter.show_current.assert_called_once()
    
    # Move next (1 to 2)
    presenter.on_next_solution()
    assert presenter.current_index == 2
    
    # Move next (at 2) - should not increment (max is 2)
    presenter.show_current.reset_mock()
    presenter.on_next_solution()
    assert presenter.current_index == 2
    presenter.show_current.assert_not_called()
