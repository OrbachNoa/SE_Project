"""
Test suite for ClusterCardWidget.

Scope   : Validates GUI logic for semantic keyword parsing and translating
          it into CSS object names (pill-positive, pill-negative, etc.).
          Also verifies that interaction signals (open/compare) are emitted.
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-CCW-001..002
"""
from PyQt6.QtWidgets import QLabel, QPushButton

from src.application.viewmodels.ClusterViewModel import ClusterCardViewModel
from src.gui.features.clusters.widgets.ClusterCardWidget import ClusterCardWidget


# ===========================================================================
# TC-CCW-001: Semantic keyword parsing correctly assigns pill styles.
# ===========================================================================
def test_cluster_card_semantic_pill_parsing(qapp):
    # Arrange
    # A single string with multiple segments separated by semicolons
    # It contains one of each type.
    desc = "More breathing room; many clashes; short window; something else"
    vm = ClusterCardViewModel(
        cluster_id=1,
        title="Test Cluster",
        size=10,
        sampled=False,
        estimated_population_size=10,
        description=desc,
        summary={}
    )

    # Act
    card = ClusterCardWidget(vm)

    # Assert
    # Extract all the pill labels
    pill_widget = card.findChild(QLabel, "pill-positive")
    assert pill_widget is not None
    assert pill_widget.text() == "More breathing room"

    pill_widget_neg = card.findChild(QLabel, "pill-negative")
    assert pill_widget_neg is not None
    assert pill_widget_neg.text() == "many clashes"

    pill_widget_span = card.findChild(QLabel, "pill-span")
    assert pill_widget_span is not None
    assert pill_widget_span.text() == "short window"

    pill_widget_neu = card.findChild(QLabel, "pill-neutral")
    assert pill_widget_neu is not None
    assert pill_widget_neu.text() == "something else"


# ===========================================================================
# TC-CCW-002: clicking the real "Open" button emits open_requested carrying
# this card's cluster_id — driving the actual QPushButton, not the signal.
# ===========================================================================
def test_cluster_card_open_button_emits_open_requested(qapp):
    # Arrange
    vm = ClusterCardViewModel(
        cluster_id=42,
        title="Test",
        size=10,
        sampled=False,
        estimated_population_size=10,
        description="",
        summary={}
    )
    card = ClusterCardWidget(vm)
    emitted_opens = []
    card.open_requested.connect(emitted_opens.append)

    # Act — find and click the actual "Open" button on the card.
    open_btn = next(b for b in card.findChildren(QPushButton) if b.text() == "Open ▶")
    open_btn.click()

    # Assert — the click emitted open_requested with this card's id.
    assert emitted_opens == [42]
