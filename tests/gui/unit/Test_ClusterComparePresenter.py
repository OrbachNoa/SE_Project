"""
Test suite for ClusterComparePresenter.

Scope   : Verifies fetching cluster comparisons and navigation to overlay.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-CLC-001..002
"""
import pytest
from unittest.mock import MagicMock
from src.gui.features.clusters.ClusterComparePresenter import ClusterComparePresenter


# TC-GUI-CLC-001
# ClusterComparePresenter must fetch and render comparison on enter.
def test_cluster_compare_renders_on_enter():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = ClusterComparePresenter(view, controller, router)
    presenter.set_pair(3, 4)
    
    controller.get_cluster_comparison.return_value = "fake_comparison"
    
    # Act
    presenter.on_enter()
    
    # Assert
    controller.get_cluster_comparison.assert_called_once_with(3, 4)
    view.render_comparison.assert_called_once_with("fake_comparison")


# TC-GUI-CLC-002
# ClusterComparePresenter must navigate to the overlay screen with correct pairs.
def test_cluster_compare_navigates_to_overlay():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    overlay_screen = MagicMock()
    
    router.get_screen.return_value = overlay_screen
    
    presenter = ClusterComparePresenter(view, controller, router)
    presenter.set_pair(3, 4)
    
    # Act
    presenter.on_view_calendar()
    
    # Assert
    overlay_screen.set_pair.assert_called_once_with(3, 4)
    router.show.assert_called_once()
    assert "cluster_calendar_overlay" in router.show.call_args[0][0]
