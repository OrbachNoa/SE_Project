from gui.core.styles.ClusterStyles import CLUSTER_STYLESHEET
from gui.core.styles.Palette import (
    COLOR_OVERLAY_A,
    COLOR_OVERLAY_B,
    COLOR_OVERLAY_MUTUAL,
)


def test_overlay_legend_swatch_styles_are_defined_after_generic_label_rule():
    generic_idx = CLUSTER_STYLESHEET.index("QFrame#legend-panel QLabel {")
    swatch_a_idx = CLUSTER_STYLESHEET.index("QFrame#legend-panel QLabel#overlay-legend-a")
    swatch_b_idx = CLUSTER_STYLESHEET.index("QFrame#legend-panel QLabel#overlay-legend-b")
    swatch_mutual_idx = CLUSTER_STYLESHEET.index("QFrame#legend-panel QLabel#overlay-legend-mutual")

    assert generic_idx < swatch_a_idx < swatch_b_idx < swatch_mutual_idx
    assert f"background-color: {COLOR_OVERLAY_A};" in CLUSTER_STYLESHEET
    assert f"background-color: {COLOR_OVERLAY_B};" in CLUSTER_STYLESHEET
    assert f"background-color: {COLOR_OVERLAY_MUTUAL};" in CLUSTER_STYLESHEET
