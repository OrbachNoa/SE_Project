"""
Test suite for MetricWidgetFactory.

Scope   : Validates GUI logic for creating metric progress bars and labels,
          ensuring correct tooltips, object names, and property assignment
          for styling (e.g. defining properties).
Pattern : AAA (Arrange / Act / Assert)
Naming  : test_<component>_<scenario>
TC-IDs  : TC-MWF-001
"""
from PyQt6.QtWidgets import QLabel, QWidget, QProgressBar

from src.gui.features.clusters.widgets.MetricWidgetFactory import create_metric_widgets


# ===========================================================================
# TC-MWF-001: Factory creates correctly configured name, indicator, and value
# ===========================================================================
def test_metric_widget_factory_creates_widgets(qapp):
    # Arrange
    crit_key = "test_crit"
    label_txt = "Test Metric"
    value = "85"
    min_max = {"test_crit": ("0", "100")}

    # Act
    name_lbl, indicator_widget, val_lbl = create_metric_widgets(
        crit_key, label_txt, value, min_max, is_defining=True
    )

    # Assert
    assert isinstance(name_lbl, QLabel)
    assert name_lbl.text() == "Test Metric"
    assert name_lbl.property("defining") is True

    assert isinstance(val_lbl, QLabel)
    assert val_lbl.text() == "85"

    assert isinstance(indicator_widget, QWidget)
    bar = indicator_widget.findChild(QProgressBar)
    assert bar is not None
    assert bar.property("defining") is True
