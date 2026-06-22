"""Cluster screen component styling rules."""

from gui.core.styles.Palette import (
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_BORDER, COLOR_MUTED,
    COLOR_TEXT, COLOR_BG
)

CLUSTER_STYLESHEET = f"""
/* ── Nav Bar Labels & Inputs ────────────────────────────────────── */
QFrame#nav-bar QLabel {{
    background: transparent;
}}

/* ── QSpinBox Styling ────────────────────────────────────────────── */
QSpinBox#k-spin {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding-left: 8px;
    padding-right: 20px;
    color: {COLOR_TEXT};
    font-size: 13px;
    min-height: 28px;
}}
QSpinBox#k-spin:hover {{
    border-color: {COLOR_PRIMARY};
}}
QSpinBox#k-spin:focus {{
    border-color: {COLOR_PRIMARY};
}}
QSpinBox#k-spin:disabled {{
    background-color: #F1F5F9;
    border-color: #E2E8F0;
    color: {COLOR_MUTED};
}}
QSpinBox#k-spin::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #CBD5E1;
    border-top-right-radius: 8px;
    background-color: #F8FAFC;
    image: url("data/assets/up-svg.svg");
}}
QSpinBox#k-spin::up-button:hover {{
    background-color: #E2E8F0;
}}
QSpinBox#k-spin::up-button:disabled {{
    image: url("data/assets/up-disabled-svg.svg");
}}
QSpinBox#k-spin::up-arrow {{
    image: none;
}}
QSpinBox#k-spin::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: 1px solid #CBD5E1;
    border-bottom-right-radius: 8px;
    background-color: #F8FAFC;
    image: url("data/assets/down-svg.svg");
}}
QSpinBox#k-spin::down-button:hover {{
    background-color: #E2E8F0;
}}
QSpinBox#k-spin::down-button:disabled {{
    image: url("data/assets/down-disabled-svg.svg");
}}
QSpinBox#k-spin::down-arrow {{
    image: none;
}}

/* ── Clustering Request Bar ──────────────────────────────────────── */
QFrame#clustering-request-bar {{
    background-color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_PRIMARY_HOVER};
    border-radius: 12px;
}}
QFrame#clustering-request-bar QLabel {{
    color: #FFFFFF;
    background: transparent;
}}
QFrame#clustering-request-bar QLabel#interpretation-label {{
    color: #E0F2FE;
    font-style: italic;
    background: transparent;
}}
QFrame#clustering-request-bar QLineEdit {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 6px 12px;
    color: {COLOR_TEXT};
    font-size: 13px;
}}
QFrame#clustering-request-bar QLineEdit:focus {{
    border-color: {COLOR_PRIMARY_HOVER};
}}
QFrame#clustering-request-bar QPushButton {{
    background-color: rgba(255, 255, 255, 0.15);
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.25);
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 600;
}}
QFrame#clustering-request-bar QPushButton:hover {{
    background-color: rgba(255, 255, 255, 0.25);
}}
QFrame#clustering-request-bar QPushButton:disabled {{
    background-color: transparent;
    color: rgba(255, 255, 255, 0.35);
    border-color: rgba(255, 255, 255, 0.08);
}}
QFrame#clustering-request-bar QProgressBar {{
    background-color: rgba(255, 255, 255, 0.2);
}}
QFrame#clustering-request-bar QProgressBar::chunk {{
    background-color: #FFFFFF;
}}

/* ── Cluster Card Widgets ────────────────────────────────────────── */
QFrame#card QLabel {{
    background: transparent;
}}
QFrame#card QFrame {{
    background: transparent;
    border: none;
}}
"""
