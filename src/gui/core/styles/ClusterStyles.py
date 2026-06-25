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
    background-color: #F8F5F0;
    border: 1px solid #E4DFD5;
    border-radius: 12px;
}}
QFrame#clustering-request-bar QLabel {{
    color: {COLOR_TEXT};
    background: transparent;
}}
QFrame#clustering-request-bar QLabel#interpretation-label {{
    color: #0369A1;
    background-color: #E6F4F8;
    border: 1px solid #BCE3EE;
    border-radius: 6px;
    padding: 6px 12px;
    font-style: normal;
    font-weight: 500;
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
    border-color: {COLOR_PRIMARY};
}}
QFrame#clustering-request-bar QPushButton {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    border: 1px solid {COLOR_PRIMARY_HOVER};
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: 600;
}}
QFrame#clustering-request-bar QPushButton:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}
QFrame#clustering-request-bar QPushButton:disabled {{
    background-color: #E2E8F0;
    color: #94A3B8;
    border-color: #CBD5E1;
}}
QFrame#clustering-request-bar QProgressBar {{
    background-color: #E2E8F0;
}}
QFrame#clustering-request-bar QProgressBar::chunk {{
    background-color: {COLOR_PRIMARY};
}}

/* ── Cluster Card Widgets ────────────────────────────────────────── */
QFrame#card QLabel {{
    background: transparent;
}}
QFrame#card QFrame {{
    background: transparent;
    border: none;
}}
QFrame#card[selected="true"] {{
    border: 2px solid {COLOR_PRIMARY};
    background-color: #EBF8FA;
    padding: 3px;
}}
QFrame#card QPushButton#btn-ghost:checked {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    font-weight: 600;
    border-radius: 6px;
    padding: 6px 12px;
}}
QFrame#card QPushButton#btn-ghost:checked:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}
QFrame#card QPushButton#more-metrics-btn {{
    font-size: 11px;
    color: #0f766e;
    text-align: left;
    padding-left: 0px;
    background: transparent;
    border: none;
}}
QFrame#card QPushButton#more-metrics-btn:hover {{
    text-decoration: underline;
    color: #0d5c56;
}}
QFrame#card QToolTip {{
    background-color: #F5F5F4;
    color: #3E352F;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}
QFrame#card QLabel#card-title {{
    font-size: 15px;
    color: #2B2521;
    font-weight: bold;
}}
QFrame#card QLabel#card-size-label {{
    color: #0f766e;
    font-weight: 600;
    font-size: 12px;
}}
QWidget#card-pills-widget {{
    background: transparent;
}}
QFrame#card QLabel#pill-positive {{
    background-color: #DCFCE7;
    color: #15803D;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: bold;
}}
QFrame#card QLabel#pill-negative {{
    background-color: #FEE2E2;
    color: #B91C1C;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: bold;
}}
QFrame#card QLabel#pill-span {{
    background-color: #E0F2FE;
    color: #0369A1;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: bold;
}}
QFrame#card QLabel#pill-neutral {{
    background-color: #F5F5F4;
    color: #57534E;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 10px;
    font-weight: bold;
}}
QWidget#profile-indicator-container {{
    background: transparent;
}}
QFrame#card QProgressBar#profile-progress {{
    background-color: #E2E8F0;
    border: none;
    border-radius: 2px;
}}
QFrame#card QProgressBar#profile-progress::chunk {{
    background-color: {COLOR_PRIMARY};
    border-radius: 2px;
}}
QFrame#card QProgressBar#profile-progress[defining="true"]::chunk {{
    background-color: #0f766e;
}}
QFrame#card QLabel#profile-status-check {{
    color: #16A34A;
    font-weight: bold;
    font-size: 13px;
    background: transparent;
}}
QFrame#card QLabel#profile-status-warning {{
    color: #EA580C;
    font-weight: bold;
    font-size: 13px;
    background: transparent;
}}
QFrame#card QLabel#profile-status-danger {{
    color: #DC2626;
    font-weight: bold;
    font-size: 13px;
    background: transparent;
}}
QFrame#card QLabel#profile-metric-name {{
    color: #555;
    font-size: 12px;
    background: transparent;
}}
QFrame#card QLabel#profile-metric-name[defining="true"] {{
    color: #0f766e;
    font-weight: bold;
}}
QFrame#card QLabel#profile-metric-value {{
    color: #333;
    font-weight: 500;
    font-size: 12px;
    background: transparent;
}}
QFrame#card QLabel#profile-metric-value[defining="true"] {{
    color: #0f766e;
    font-weight: bold;
}}
QFrame#composite-container {{
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 6px;
    margin-top: 4px;
    margin-bottom: 4px;
}}
QLabel#composite-label-name {{
    color: #475569;
    font-size: 11px;
    font-weight: bold;
    background: transparent;
}}
QLabel#composite-label-value {{
    font-size: 12px;
    font-weight: bold;
    background: transparent;
}}
QLabel#composite-label-value[rating="high"] {{
    color: #16A34A;
}}
QLabel#composite-label-value[rating="low"] {{
    color: #DC2626;
}}
QLabel#composite-label-value[rating="medium"] {{
    color: #D97706;
}}
QLabel#composite-label-value[rating="wide"] {{
    color: #16A34A;
}}
QLabel#composite-label-value[rating="tight"] {{
    color: #DC2626;
}}

/* ── All Metrics Dialog ─────────────────────────────────────────── */
QDialog#all-metrics-dialog {{
    background-color: #FFFFFF;
    border-radius: 8px;
}}
QLabel#all-metrics-header {{
    color: #0f766e;
    font-size: 16px;
    margin-bottom: 8px;
}}
QScrollArea#all-metrics-scroll {{
    background-color: transparent;
    border: none;
}}
QDialog#all-metrics-dialog QFrame#card {{
    background-color: transparent;
    border: none;
}}
"""
