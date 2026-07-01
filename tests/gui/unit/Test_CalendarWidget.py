"""
Test suite for CalendarWidget.

Scope   : Validates GUI logic for clicking day cells and setting excluded styles.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CAL-001..002
"""
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QFrame

from src.gui.common.components.CalendarWidget import CalendarWidget, ClickableDayCell


# ===========================================================================
# TC-CAL-001: set_date_excluded_style updates the objectName for CSS
# ===========================================================================
def test_calendar_widget_sets_excluded_style(qapp):
    # Arrange
    widget = CalendarWidget()
    target_frame = QFrame()
    widget._day_frames = {"2026-07-01": target_frame}

    # Act 1 - Set Excluded
    widget.set_date_excluded_style("2026-07-01", True)

    # Assert 1
    assert target_frame.objectName() == "calendar-cell-excluded"

    # Act 2 - Set Not Excluded
    widget.set_date_excluded_style("2026-07-01", False)

    # Assert 2
    assert target_frame.objectName() == "calendar-cell-included"


# ===========================================================================
# TC-CAL-002: ClickableDayCell emits clicked signal on left click
# ===========================================================================
def test_calendar_widget_emits_date_clicked(qapp):
    # Arrange
    cell = ClickableDayCell()
    emitted = []
    cell.clicked.connect(lambda: emitted.append(True))

    # Create a dummy left mouse click event
    click_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(0.0, 0.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )

    # Act
    cell.mousePressEvent(click_event)

    # Assert
    assert len(emitted) == 1
