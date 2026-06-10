"""Screen layout and sub-panel styling rules."""

from gui.core.styles.Palette import (
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_BORDER, COLOR_MUTED,
    COLOR_TEXT, COLOR_BG, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER
)

SCREEN_STYLESHEET = f"""
/* ── Cards ──────────────────────────────────────────────────────── */
QFrame#card {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 4px;
}}
QFrame#selector-card {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 14px;
}}
QFrame#selector-card:hover {{
    border-color: {COLOR_PRIMARY};
}}
QLabel#card-title {{
    color: {COLOR_TEXT};
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}}
QLabel#card-hint {{
    color: {COLOR_MUTED};
    font-size: 11px;
    background: transparent;
}}

/* ── Status pills ────────────────────────────────────────────────── */
QLabel#status-ok {{
    color: {COLOR_SUCCESS};
    font-size: 12px;
    font-weight: 600;
    background: transparent;
}}
QLabel#status-pending {{
    color: {COLOR_MUTED};
    font-size: 12px;
    background: transparent;
}}
QLabel#status-warning {{
    color: {COLOR_WARNING};
    font-size: 14px;
    font-weight: bold;
    padding-bottom: 10px;
    background: transparent;
}}
QLabel#status-error {{
    color: {COLOR_DANGER};
    font-size: 12px;
    background: transparent;
}}

/* ── Nav bar (output screen) ─────────────────────────────────────── */
QFrame#nav-bar {{
    background-color: #FFFFFF;
    border-bottom: 1px solid {COLOR_BORDER};
}}
QLabel#counter-label {{
    color: {COLOR_TEXT};
    font-size: 14px;
    font-weight: 600;
    background: transparent;
    min-width: 340px;
}}

/* ── Content area ────────────────────────────────────────────────── */
QFrame#content-area {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
}}
QLabel#content-placeholder {{
    color: {COLOR_MUTED};
    font-size: 14px;
    background: transparent;
}}
QLabel#schedule-text {{
    color: {COLOR_TEXT};
    font-size: 12px;
    font-family: "Consolas", "Courier New", monospace;
    background: transparent;
}}

/* ── Action bar ──────────────────────────────────────────────────── */
QFrame#action-bar {{
    background-color: #FFFFFF;
    border-bottom: 1px solid {COLOR_BORDER};
}}
QLabel#mode-label {{
    color: #64748B;
    background: transparent;
}}

/* ── Info bar ────────────────────────────────────────────────────── */
QFrame#info-bar {{
    background-color: {COLOR_BG};
    border-bottom: 1px solid {COLOR_BORDER};
}}

/* ── Status badges ───────────────────────────────────────────────── */
QLabel#badge {{
    background-color: #F1F5F9;
    color: #8A7E72;
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
}}
QLabel#badge-ok {{
    background-color: #E8F5E9;
    color: {COLOR_SUCCESS};
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#badge-warning {{
    background-color: #FEF3C7;
    color: #92400E;
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}}

/* ── Month/Period navigation bar ─────────────────────────────────── */
QFrame#month-nav-bar {{
    background-color: {COLOR_PRIMARY};
    border-bottom: 1px solid {COLOR_PRIMARY_HOVER};
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}}
QFrame#month-nav-bar QLabel {{
    color: #FFFFFF;
    font-size: 15px;
    font-weight: bold;
    background: transparent;
}}
QFrame#month-nav-bar QPushButton {{
    background-color: rgba(255, 255, 255, 0.15);
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
}}
QFrame#month-nav-bar QPushButton:hover {{
    background-color: rgba(255, 255, 255, 0.25);
}}
QFrame#month-nav-bar QPushButton:disabled {{
    background-color: transparent;
    color: rgba(255, 255, 255, 0.35);
    border-color: rgba(255, 255, 255, 0.08);
}}

/* ── Exporter and solution bar components ───────────────────────── */
QPushButton#btn-export {{
    background-color: {COLOR_PRIMARY};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 0 18px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton#btn-export:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}
QPushButton#btn-export:disabled {{
    background-color: #CBD5E1;
    color: #F1F5F9;
}}
QLabel#solution-counter-label {{
    min-width: 150px;
    font-weight: 600;
    font-size: 12px;
    color: {COLOR_TEXT};
    background: transparent;
}}
QLabel#page-label {{
    min-width: 90px;
    font-weight: 600;
    font-size: 12px;
    color: {COLOR_TEXT};
    background: transparent;
}}
QPushButton#btn-page-arrow {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT};
    border: 1px solid #D5CFC9;
    border-radius: 8px;
    padding: 0px;
}}
QPushButton#btn-page-arrow:hover {{
    background-color: {COLOR_BG};
    border-color: {COLOR_PRIMARY};
}}
QPushButton#btn-page-arrow:disabled {{
    color: #D5CFC9;
    border-color: {COLOR_BORDER};
}}

/* ── Program Selector Card & Placeholder ───────────────────────── */
QLabel#card-icon {{
    background: transparent;
    border: none;
}}
QLabel#card-placeholder {{
    color: #94A3B8;
    font-size: 13px;
    background: transparent;
}}
QLabel#program-chip {{
    color: {COLOR_TEXT};
    background-color: #FAF5EC;
    border: 1px solid {COLOR_PRIMARY};
    border-radius: 11px;
    padding: 3px 10px;
    font-size: 11px;
}}
QFrame#calendar-placeholder {{
    border: 2px dashed #CBD5E1;
    border-radius: 16px;
    background-color: #FFFFFF;
}}
QLabel#calendar-placeholder-icon {{
    font-size: 30px;
    background: transparent;
    border: none;
}}
QLabel#calendar-placeholder-title {{
    color: #94A3B8;
    font-size: 14px;
    font-weight: 600;
    background: transparent;
    border: none;
}}
QLabel#calendar-placeholder-subtitle {{
    color: #B6C0CC;
    font-size: 11px;
    background: transparent;
    border: none;
}}
"""
