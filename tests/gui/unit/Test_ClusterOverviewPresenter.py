"""
Test suite for ClusterOverviewPresenter.

Scope   : Verifies cluster compute lifecycle, card selection, and navigation.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-CLO-001..003
"""
from unittest.mock import MagicMock, patch
from src.gui.features.clusters.ClusterOverviewPresenter import ClusterOverviewPresenter


# TC-GUI-CLO-001
# ClusterOverviewPresenter must block applying K if K <= 0.
def test_cluster_overview_invalid_k():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    
    presenter = ClusterOverviewPresenter(view, controller, MagicMock(), MagicMock(), MagicMock())
    
    # Act
    presenter.on_apply_k(0)
    
    # Assert
    view.show_message.assert_called_once_with("K must be a positive integer.")
    controller.cluster.assert_not_called()


# TC-GUI-CLO-002
# ClusterOverviewPresenter must manage compare selections up to 2 items.
def test_cluster_overview_compare_toggled():
    # Arrange
    view = MagicMock()
    presenter = ClusterOverviewPresenter(view, MagicMock(), MagicMock(), MagicMock(), MagicMock())
    
    # Act / Assert
    # Select first
    presenter.on_compare_toggled(1, True)
    assert presenter._compare_selection == [1]
    view.set_compare_enabled.assert_called_with(False)
    
    # Select second
    presenter.on_compare_toggled(2, True)
    assert presenter._compare_selection == [1, 2]
    view.set_compare_enabled.assert_called_with(True)
    
    # Deselect first
    presenter.on_compare_toggled(1, False)
    assert presenter._compare_selection == [2]
    view.set_compare_enabled.assert_called_with(False)


# TC-GUI-CLO-003
# ClusterOverviewPresenter must navigate to compare screen when compare is clicked with 2 items.
def test_cluster_overview_compare_clicked():
    # Arrange
    view = MagicMock()
    view.compare_screen_name.return_value = "cluster_compare"
    router = MagicMock()
    compare_screen = MagicMock()
    presenter = ClusterOverviewPresenter(view, MagicMock(), router, MagicMock(), compare_screen)
    
    # Act - with less than 2 items (should do nothing)
    presenter._compare_selection = [1]
    presenter.on_compare()
    router.show.assert_not_called()
    
    # Act - with exactly 2 items
    presenter._compare_selection = [1, 2]
    presenter.on_compare()
    
    # Assert
    compare_screen.set_pair.assert_called_once_with(1, 2)
    router.show.assert_called_once_with("cluster_compare")
