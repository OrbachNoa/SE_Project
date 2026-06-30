"""
Test suite for ClusterDetailPresenter.

Scope   : Verifies schedule navigation inside a cluster, expired state handling, and updates.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-CLD-001..003
"""
from unittest.mock import MagicMock
from src.gui.features.clusters.ClusterDetailPresenter import ClusterDetailPresenter


# TC-GUI-CLD-001
# ClusterDetailPresenter must handle expired clustering session on entry.
def test_cluster_detail_handles_expired_session():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    # Simulate empty cluster size (expired)
    controller.get_cluster_size.return_value = 0
    presenter = ClusterDetailPresenter(view, controller, router)
    presenter.set_cluster(1)
    
    # Act
    presenter.on_enter()
    
    # Assert
    view.show_message.assert_called_once()
    assert "expired" in view.show_message.call_args[0][0]
    router.back.assert_called_once()


# TC-GUI-CLD-002
# ClusterDetailPresenter must handle search finished notification by navigating back.
def test_cluster_detail_handles_search_finished():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = ClusterDetailPresenter(view, controller, router)
    presenter._is_active = True
    
    # Act
    presenter._on_search_finished()
    
    # Assert
    view.show_message.assert_called_once()
    assert "New results have finished generating" in view.show_message.call_args[0][0]
    router.back.assert_called_once()
    
    # Ensure notice is only shown once
    view.reset_mock()
    router.reset_mock()
    presenter._on_search_finished()
    view.show_message.assert_not_called()
    router.back.assert_not_called()


# TC-GUI-CLD-003
# ClusterDetailPresenter must navigate schedule bounds safely.
def test_cluster_detail_navigation_bounds():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = ClusterDetailPresenter(view, controller, router)
    presenter._show_current = MagicMock()
    
    presenter.set_cluster(1)
    presenter._size = 2  # 0 and 1 are valid indices
    
    # Act / Assert
    # Move previous (at 0) - should not decrement
    presenter.on_prev()
    assert presenter._index == 0
    presenter._show_current.assert_not_called()
    
    # Move next (0 to 1)
    presenter.on_next()
    assert presenter._index == 1
    presenter._show_current.assert_called_once()
    
    # Move next (at 1) - should not increment (max is 1)
    presenter._show_current.reset_mock()
    presenter.on_next()
    assert presenter._index == 1
    presenter._show_current.assert_not_called()
