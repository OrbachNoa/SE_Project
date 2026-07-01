"""
Test suite for OverlayCalendarWidget.

Scope   : Validates GUI logic for rendering shared vs differing schedules
          by assigning specific 'overlay-badge' CSS class names.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-OVW-001
"""
from PyQt6.QtWidgets import QLabel, QVBoxLayout

from src.gui.features.clusters.widgets.OverlayCalendarWidget import OverlayCalendarWidget
from src.application.viewmodels.ScheduleViewModel import ScheduleItemViewModel


# ===========================================================================
# TC-OVW-001: OverlayCalendarWidget tags items correctly for CSS styling.
# ===========================================================================
def test_overlay_calendar_tags_badges_correctly(qapp):
    # Arrange
    widget = OverlayCalendarWidget()

    # Mock a day layout to catch the added labels
    mock_layout = QVBoxLayout()
    widget._day_layouts = {"2026-07-01": mock_layout}

    # Create ScheduleItemViewModels
    # date, title, subtitle, tooltip, instructor, evaluation, course_id, programs
    item_a = ScheduleItemViewModel("2026-07-01", "TitleA", "html", "tool", "", "", "courseA", [])
    item_b = ScheduleItemViewModel("2026-07-01", "TitleB", "html", "tool", "", "", "courseB", [])
    item_mutual = ScheduleItemViewModel("2026-07-01", "TitleC", "html", "tool", "", "", "courseC", [])

    items = [
        (item_a, "family_a"),
        (item_b, "family_b"),
        (item_mutual, "mutual")
    ]

    # Act
    widget.display_overlay_assignments(items)

    # Assert
    # 3 items should have been added
    assert mock_layout.count() == 3

    label_a = mock_layout.itemAt(0).widget()
    label_b = mock_layout.itemAt(1).widget()
    label_mutual = mock_layout.itemAt(2).widget()

    assert isinstance(label_a, QLabel)
    assert label_a.objectName() == "overlay-badge-a"

    assert isinstance(label_b, QLabel)
    assert label_b.objectName() == "overlay-badge-b"

    assert isinstance(label_mutual, QLabel)
    assert label_mutual.objectName() == "overlay-badge-mutual"
