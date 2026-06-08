"""Baseline control styling rules for PyQt6 widgets."""

from gui.core.styles.Palette import (
    COLOR_BG, COLOR_TEXT, COLOR_PRIMARY, COLOR_PRIMARY_HOVER,
    COLOR_BORDER, COLOR_MUTED, COLOR_DANGER, COLOR_WARNING, COLOR_SUCCESS
)

GLOBAL_STYLESHEET = f"""
/* ── Base widget defaults ─────────────────────────────────────────── */
QWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
}}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {{
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    border: none;
    outline: none;
}}
QPushButton#btn-primary {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 20px;
}}
QPushButton#btn-primary:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}
QPushButton#btn-primary:disabled {{
    background-color: {COLOR_BORDER};
    color: {COLOR_MUTED};
}}
QPushButton#btn-secondary {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT};
    border: 1px solid #D5CFC9;
    border-radius: 8px;
    padding: 6px 14px;
}}
QPushButton#btn-secondary:hover {{
    background-color: {COLOR_BG};
    border-color: {COLOR_PRIMARY};
}}
QPushButton#btn-secondary:disabled {{
    color: #D5CFC9;
    border-color: {COLOR_BORDER};
}}
QPushButton#btn-danger {{
    background-color: #FFFFFF;
    color: {COLOR_DANGER};
    border: 1px solid #FCA5A5;
}}
QPushButton#btn-danger:hover {{
    background-color: #FEF2F2;
    border-color: #F87171;
}}
QPushButton#btn-ghost {{
    background-color: transparent;
    color: #8A7E72;
    border: none;
    font-size: 13px;
}}
QPushButton#btn-ghost:hover {{
    color: {COLOR_PRIMARY};
    background-color: {COLOR_BG};
}}

/* ── Radio buttons ───────────────────────────────────────────────── */
QRadioButton {{
    background: transparent;
    color: {COLOR_TEXT};
    spacing: 6px;
}}
QRadioButton::indicator {{
    width: 15px;
    height: 15px;
    border-radius: 8px;
    border: 2px solid #D5CFC9;
    background: #FFFFFF;
}}
QRadioButton::indicator:checked {{
    border-color: {COLOR_PRIMARY};
    background: {COLOR_PRIMARY};
}}

/* ── Progress bar ────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {COLOR_BORDER};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {COLOR_SUCCESS};
    border-radius: 4px;
}}

/* ── Divider ─────────────────────────────────────────────────────── */
QFrame#divider {{
    background-color: {COLOR_BORDER};
    border: none;
    max-height: 1px;
}}
QFrame#vertical-divider {{
    color: {COLOR_BORDER};
}}

/* ── Tooltips ────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {COLOR_TEXT};
    color: {COLOR_BG};
    border: 1px solid #2B2521;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Scroll areas ────────────────────────────────────────────────── */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    width: 6px;
    background: transparent;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1;
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_MUTED};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}

/* ── Group boxes ─────────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    margin-top: 8px;
    font-weight: 600;
    color: {COLOR_TEXT};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}}
"""
