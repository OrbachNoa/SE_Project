"""Stylesheets specifically for dialog chrome (modal popups)."""

from gui.core.styles.Palette import (
    COLOR_PRIMARY, COLOR_PRIMARY_HOVER, COLOR_BORDER, COLOR_BG, COLOR_TEXT
)

DIALOG_STYLESHEET = f"""
/* ── Program Selector Dialog ───────────────────────────────────────── */
QDialog {{
    background-color: #FAFAFA;
}}
QFrame#dialog-card {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 18px;
}}
QLabel#dialog-title {{
    color: {COLOR_TEXT};
    font-size: 17px;
    font-weight: 700;
    background: transparent;
}}
QLabel#dialog-hint {{
    color: #8A7E72;
    font-size: 12px;
    background: transparent;
}}
QLabel#dialog-counter {{
    color: {COLOR_TEXT};
    font-size: 12px;
    font-weight: 600;
    background: #FAF5EC;
    border-radius: 11px;
    padding: 4px 12px;
}}
QPushButton#dialog-select {{
    background-color: {COLOR_PRIMARY};
    color: #FDFBF7;
    border: none;
    border-radius: 10px;
    padding: 10px 26px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#dialog-select:hover {{
    background-color: {COLOR_PRIMARY_HOVER};
}}
QPushButton#dialog-cancel {{
    background-color: #FFFFFF;
    color: #64748B;
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 13px;
}}
QPushButton#dialog-cancel:hover {{
    background-color: #F1F5F9;
    border-color: #CBD5E1;
}}

/* ── Program Selector Cards ───────────────────────────────────────── */
QFrame#prog-card {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
}}
QFrame#prog-card:hover {{
    border-color: #CBD5E1;
}}
QFrame#prog-card[selected="true"] {{
    background-color: #FAF5EC;
    border: 2px solid {COLOR_PRIMARY};
}}

/* ── Program Card box indicator ───────────────────────────────────── */
QLabel#prog-card-box {{
    background: #FFFFFF;
    border: 2px solid #CBD5E1;
    border-radius: 6px;
}}
QLabel#prog-card-box[selected="true"] {{
    color: #FFFFFF;
    background: {COLOR_PRIMARY};
    border: 2px solid {COLOR_PRIMARY};
    font-weight: bold;
    font-size: 12px;
}}

/* ── Program Card Labels ─────────────────────────────────────────── */
QLabel#prog-card-id {{
    color: #64748B;
    font-size: 11px;
    background: transparent;
    border: none;
}}
QLabel#prog-card-id[selected="true"] {{
    color: {COLOR_PRIMARY};
    font-weight: 600;
}}

QLabel#prog-card-name {{
    color: #334155;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
    border: none;
}}
QLabel#prog-card-name[selected="true"] {{
    color: {COLOR_TEXT};
    font-weight: 700;
}}
"""


SETTINGS_DIALOG_STYLESHEET = """
QFrame#settings-row {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}
QLabel#settings-row-title {
    font-size: 13px;
    font-weight: 600;
    color: #3E352F;
    background: transparent;
}
QLabel#settings-row-desc {
    font-size: 12px;
    color: #8A7E72;
    background: transparent;
}
QSpinBox {
    border: 1px solid #D5CFC9;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 13px;
    background: #FFFFFF;
    color: #3E352F;
}
QSpinBox:disabled {
    color: #C4BAB4;
    background: #F8F5F1;
    border-color: #EDE9E3;
}
QCheckBox {
    background: transparent;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #D5CFC9;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    border-color: #3396ad;
    background: #3396ad;
}
"""