"""Course list component styling rules."""

from gui.core.styles.Palette import (
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_BORDER, COLOR_MUTED,
    COLOR_TEXT, COLOR_BG, COLOR_SUCCESS
)

COURSE_LIST_STYLESHEET = f"""
/* ── Program Header Button (Expandable Blocks) ──────────────────── */
QPushButton#course-list-header-btn {{
    background-color: {COLOR_PRIMARY};
    color: {COLOR_BG};
    border-radius: 8px;
    text-align: left;
    padding: 8px 14px;
    font-family: 'Segoe UI Symbol', 'Segoe UI';
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#course-list-header-btn:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}

/* ── Course Rows & Lists ────────────────────────────────────────── */
QWidget#course-row-exam {{
    background-color: #F0FAF5;
    border-left: 3px solid {COLOR_SUCCESS};
    border-radius: 0 4px 4px 0;
}}
QWidget#course-row-default {{
    background-color: #FFFFFF;
    border-left: 3px solid {COLOR_BORDER};
    border-radius: 0 4px 4px 0;
}}
QLabel#course-id-lbl {{
    color: #64748B;
    background: transparent;
    font-family: 'Segoe UI';
    font-size: 10px;
}}
QLabel#course-name-lbl {{
    color: #1E293B;
    background: transparent;
    font-family: 'Segoe UI';
    font-size: 12px;
}}
QLabel#course-group-lbl {{
    color: {COLOR_TEXT};
    background-color: #FAF5EC;
    padding: 4px 12px;
    border-radius: 6px;
    font-weight: 600;
    margin: 4px 0px;
    font-family: 'Segoe UI';
    font-size: 11px;
}}
QScrollArea#course-scroll-area {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}
QLabel#course-empty-lbl {{
    color: #94A3B8;
    font-size: 12px;
    background: transparent;
}}
"""
