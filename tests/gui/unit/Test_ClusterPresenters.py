"""
Test suite for the cluster GUI presenters.

Consolidates the presentation-layer tests for the four cluster screens —
ClusterOverviewPresenter, ClusterDetailPresenter, ClusterComparePresenter,
and ClusterCalendarOverlayPresenter — which previously lived in four
separate single-purpose files. Grouping them here keeps the cluster UI
presentation logic in one place; each presenter keeps its own section and
its original TC-ID family.

Scope   : Cluster overview/detail/compare/overlay presenter logic — compute
          lifecycle, K validation, in-cluster navigation bounds, expired
          session handling, comparison fetching, and overlay merge/classify.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-GUI-CLO-001..003 (overview), TC-GUI-CLD-001..005 (detail),
          TC-GUI-CLC-001..002 (compare), TC-GUI-CCO-001..002 (overlay)
"""
from unittest.mock import MagicMock

from src.gui.features.clusters.ClusterOverviewPresenter import ClusterOverviewPresenter
from src.gui.features.clusters.ClusterDetailPresenter import ClusterDetailPresenter
from src.gui.features.clusters.ClusterComparePresenter import ClusterComparePresenter
from src.gui.features.clusters.ClusterCalendarOverlayPresenter import ClusterCalendarOverlayPresenter
from src.application.viewmodels.ScheduleViewModel import ScheduleItemViewModel


# ===========================================================================
# ClusterOverviewPresenter
#   Verifies cluster compute lifecycle, card selection, and navigation.
# ===========================================================================

# TC-GUI-CLO-001
# ClusterOverviewPresenter must block applying K if K <= 0.
def test_cluster_overview_invalid_k():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    cluster_controller = MagicMock()

    presenter = ClusterOverviewPresenter(view, controller, cluster_controller, MagicMock(), MagicMock(), MagicMock())

    # Act
    presenter.on_apply_k(0)

    # Assert — no clustering work is kicked off (get_cluster_coordinator is
    # what _kick_off would call to start a run).
    view.show_message.assert_called_once_with("K must be a positive integer.")
    cluster_controller.get_cluster_coordinator.assert_not_called()


# TC-GUI-CLO-002
# ClusterOverviewPresenter must manage compare selections up to 2 items.
def test_cluster_overview_compare_toggled():
    # Arrange
    view = MagicMock()
    presenter = ClusterOverviewPresenter(view, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())

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
    presenter = ClusterOverviewPresenter(view, MagicMock(), MagicMock(), router, MagicMock(), compare_screen)

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


# ===========================================================================
# ClusterDetailPresenter
#   Verifies schedule navigation inside a cluster, expired state handling,
#   and updates.
# ===========================================================================

# TC-GUI-CLD-001
# ClusterDetailPresenter must handle expired clustering session on entry.
def test_cluster_detail_handles_expired_session():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    cluster_controller = MagicMock()
    router = MagicMock()

    # Simulate empty cluster size (expired)
    cluster_controller.get_cluster_size.return_value = 0
    presenter = ClusterDetailPresenter(view, controller, cluster_controller, router)
    presenter.set_cluster(1)

    # Act
    presenter.on_enter()

    # Assert
    view.show_message.assert_called_once()
    assert "expired" in view.show_message.call_args[0][0]


# TC-GUI-CLD-002
# ClusterDetailPresenter must handle search finished notification by navigating back.
def test_cluster_detail_handles_search_finished():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()

    presenter = ClusterDetailPresenter(view, controller, MagicMock(), router)
    presenter._is_active = True

    # Act
    presenter._on_search_finished()

    # Assert
    view.show_message.assert_called_once()
    assert "New results have finished generating" in view.show_message.call_args[0][0]

    # Ensure notice is only shown once
    view.reset_mock()
    router.reset_mock()
    presenter._on_search_finished()
    view.show_message.assert_not_called()


# TC-GUI-CLD-003
# ClusterDetailPresenter.on_prev must not move below the first schedule.
def test_cluster_detail_prev_at_lower_bound_does_not_move():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()

    presenter = ClusterDetailPresenter(view, controller, MagicMock(), router)
    presenter._show_current = MagicMock()
    presenter.set_cluster(1)
    presenter._size = 2   # valid indices are 0 and 1
    presenter._index = 0  # already at the first schedule

    # Act
    presenter.on_prev()

    # Assert — index stays at 0 and no redraw is triggered.
    assert presenter._index == 0
    presenter._show_current.assert_not_called()


# TC-GUI-CLD-004
# ClusterDetailPresenter.on_next must advance to the next schedule in range.
def test_cluster_detail_next_advances_within_bounds():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()

    presenter = ClusterDetailPresenter(view, controller, MagicMock(), router)
    presenter._show_current = MagicMock()
    presenter.set_cluster(1)
    presenter._size = 2   # valid indices are 0 and 1
    presenter._index = 0

    # Act
    presenter.on_next()

    # Assert — index advances to 1 and the new schedule is drawn once.
    assert presenter._index == 1
    presenter._show_current.assert_called_once()


# TC-GUI-CLD-005
# ClusterDetailPresenter.on_next must not move past the last schedule.
def test_cluster_detail_next_at_upper_bound_does_not_move():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    router = MagicMock()

    presenter = ClusterDetailPresenter(view, controller, MagicMock(), router)
    presenter._show_current = MagicMock()
    presenter.set_cluster(1)
    presenter._size = 2   # valid indices are 0 and 1
    presenter._index = 1  # already at the last schedule

    # Act
    presenter.on_next()

    # Assert — index stays at 1 and no redraw is triggered.
    assert presenter._index == 1
    presenter._show_current.assert_not_called()


# ===========================================================================
# ClusterComparePresenter
#   Verifies fetching cluster comparisons and navigation to overlay.
# ===========================================================================

# TC-GUI-CLC-001
# ClusterComparePresenter must fetch and render comparison on enter.
def test_cluster_compare_renders_on_enter():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    cluster_controller = MagicMock()
    router = MagicMock()

    presenter = ClusterComparePresenter(view, controller, cluster_controller, router)
    presenter.set_pair(3, 4)

    cluster_controller.get_cluster_comparison.return_value = "fake_comparison"

    # Act
    presenter.on_enter()

    # Assert
    cluster_controller.get_cluster_comparison.assert_called_once_with(3, 4)
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

    presenter = ClusterComparePresenter(view, controller, MagicMock(), router)
    presenter.set_pair(3, 4)

    # Act
    presenter.on_view_calendar()

    # Assert
    overlay_screen.set_pair.assert_called_once_with(3, 4)
    router.show.assert_called_once()
    assert "cluster_calendar_overlay" in router.show.call_args[0][0]


# ===========================================================================
# ClusterCalendarOverlayPresenter
#   Verifies fetching cluster comparison and correct merge/classification logic.
# ===========================================================================

# TC-GUI-CCO-001
# ClusterCalendarOverlayPresenter must fetch comparison and render overlay.
def test_cluster_calendar_overlay_renders_on_enter():
    # Arrange
    view = MagicMock()
    controller = MagicMock()
    cluster_controller = MagicMock()
    router = MagicMock()

    presenter = ClusterCalendarOverlayPresenter(view, controller, cluster_controller, router)
    presenter.set_pair(3, 4)

    comparison = MagicMock()
    comparison.left_title = "Title A"
    comparison.right_title = "Title B"
    comparison.left_schedule.items = []
    comparison.right_schedule.items = []

    cluster_controller.get_cluster_comparison.return_value = comparison
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
