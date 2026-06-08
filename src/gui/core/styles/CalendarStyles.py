"""Calendar component styling rules."""

from gui.core.styles.Palette import (
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_BORDER, COLOR_MUTED,
    COLOR_TEXT, COLOR_BG
)

CALENDAR_STYLESHEET = f"""
/* ── Calendar Editor Card ───────────────────────────────────────── */
QFrame#calendar-editor-card {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 14px;
}}
QPushButton#btn-calendar-nav {{
    background-color: {COLOR_PRIMARY};
    color: {COLOR_BG};
    border-radius: 4px;
    padding: 5px;
    font-weight: bold;
    border: none;
}}
QPushButton#btn-calendar-nav:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}
QPushButton#btn-calendar-nav:disabled {{
    background-color: {COLOR_BORDER};
    color: {COLOR_MUTED};
}}
QLabel#calendar-period-label {{
    font-weight: bold;
    font-size: 13px;
    color: {COLOR_TEXT};
    background: transparent;
}}
QPushButton#btn-apply-constraints {{
    background-color: {COLOR_PRIMARY};
    color: {COLOR_BG};
    padding: 8px;
    border-radius: 4px;
    font-weight: bold;
    border: none;
}}
QPushButton#btn-apply-constraints:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}

/* ── Calendar Widget Cells & Badges ──────────────────────────────── */
QLabel#calendar-month-banner {{
    font-size: 13px;
    font-weight: bold;
    color: {COLOR_PRIMARY};
    padding: 4px 0;
    background: transparent;
}}
QLabel#calendar-header-day {{
    font-weight: 600;
    color: #64748B;
    padding: 8px 4px;
    background: transparent;
}}
QLabel#calendar-month-header {{
    font-size: 14px;
    font-weight: bold;
    color: {COLOR_PRIMARY};
    padding: 12px 0 6px 0;
    background: transparent;
}}
QFrame#calendar-cell-frame {{
    background-color: #FAFAFA;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    min-height: 60px;
}}
QLabel#calendar-day-lbl {{
    font-size: 10px;
    font-weight: 700;
    color: #94A3B8;
    background: transparent;
}}
QLabel#calendar-exam-badge {{
    background-color: #FAF5EC;
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_PRIMARY};
    font-size: 11px;
    border-radius: 4px;
    padding: 2px;
}}
QFrame#calendar-cell-excluded {{
    background-color: #EAE8E6;
    border: 1px solid {COLOR_TEXT};
    border-radius: 8px;
    min-height: 60px;
}}
QFrame#calendar-cell-included {{
    background-color: #E6F4F8;
    border: 1px solid {COLOR_PRIMARY};
    border-radius: 8px;
    min-height: 60px;
}}
QFrame#calendar-cell-excluded-output {{
    background-color: #F3EFEA;
    border: 1px solid {COLOR_MUTED};
    border-radius: 8px;
    min-height: 60px;
}}
QWidget#calendar-scroll-content {{
    background: transparent;
}}
"""
