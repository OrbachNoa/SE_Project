"""Stylesheets specifically for the SortConfigPanel dialog row items."""

from gui.core.styles.Palette import (
    COLOR_TEXT, COLOR_PRIMARY, COLOR_BORDER
)

SORT_CONFIG_PANEL_STYLESHEET = f"""
QFrame#sort-row {{
    background-color: #F8FAFC;
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
}}
QFrame#sort-row[active="true"] {{
    background-color: #FFFFFF;
    border: 1px solid #9AD3DF;
}}
QLabel#sort-drag-handle {{
    font-size: 16px;
    font-weight: bold;
    color: #CBD5E1;
    background: transparent;
}}
QLabel#sort-label {{
    font-size: 13px;
    font-weight: 500;
    color: #64748B;
    background: transparent;
}}
QFrame#sort-row[active="true"] QLabel#sort-label {{
    font-weight: 600;
    color: {COLOR_TEXT};
}}
QLabel#sort-priority-badge {{
    font-size: 11px;
    font-weight: 700;
    color: #94A3B8;
    background-color: #E2E8F0;
    border-radius: 12px;
}}
QLabel#sort-priority-badge[has_rank="true"] {{
    color: #FFFFFF;
    background-color: {COLOR_PRIMARY};
}}
"""
