"""
Test suite for ClusterCalendarOverlayPresenter.

Scope   : Verifies fetching cluster comparison and correct merge/classification logic.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-CCO-001..002
"""
from unittest.mock import MagicMock
from src.gui.features.clusters.ClusterCalendarOverlayPresenter import ClusterCalendarOverlayPresenter
from src.application.viewmodels.ScheduleViewModel import ScheduleItemViewModel


# TC-GUI-CCO-001
# ClusterCalendarOverlayPresenter must fetch comparison and render overlay.
def test_cluster_calendar_overlay_renders_on_enter():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()
    
    presenter = ClusterCalendarOverlayPresenter(view, controller, router)
    presenter.set_pair(3, 4)
    
    comparison = MagicMock()
    comparison.left_title = "Title A"
    comparison.right_title = "Title B"
    comparison.left_schedule.items = []
    comparison.right_schedule.items = []
    
    controller.get_cluster_comparison.return_value = comparison
    controller.get_loaded_periods.return_value = []
    controller.get_mapper.return_value = MagicMock()
    
    # Act
    presenter.on_enter()
    
    # Assert
    view.set_titles.assert_called_once_with("Title A", "Title B")
    view.render_overlay.assert_called_once_with([])


# TC-GUI-CCO-002
# ClusterCalendarOverlayPresenter must correctly merge and classify items.
def test_cluster_calendar_overlay_merge_logic():
    # Arrange
    item1 = ScheduleItemViewModel("course1", MagicMock(), MagicMock(), MagicMock())
    item2 = ScheduleItemViewModel("course2", MagicMock(), MagicMock(), MagicMock())
    item3 = ScheduleItemViewModel("course3", MagicMock(), MagicMock(), MagicMock())
    
    # Same date/title for item1
    item1.date = "2024-01-01"
    item1.title = "Math"
    
    item1_clone = ScheduleItemViewModel("course1", MagicMock(), MagicMock(), MagicMock())
    item1_clone.date = "2024-01-01"
    item1_clone.title = "Math"
    
    # Different date/titles for others
    item2.date = "2024-01-02"
    item2.title = "Physics"
    
    item3.date = "2024-01-03"
    item3.title = "Biology"
    
    items_a = [item1, item2]
    items_b = [item1_clone, item3]
    
    # Act
    merged = ClusterCalendarOverlayPresenter._merge(items_a, items_b)
    
    # Assert
    assert len(merged) == 3
    
    mutual = [i for i, tag in merged if tag == "mutual"]
    a_only = [i for i, tag in merged if tag == "family_a"]
    b_only = [i for i, tag in merged if tag == "family_b"]
    
    assert len(mutual) == 1
    assert mutual[0].title == "Math"
    
    assert len(a_only) == 1
    assert a_only[0].title == "Physics"
    
    assert len(b_only) == 1
    assert b_only[0].title == "Biology"
