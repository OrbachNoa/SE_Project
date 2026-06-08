"""Header component styling rules."""

from gui.core.styles.Palette import COLOR_GOLD, COLOR_TEXT

HEADER_STYLESHEET = f"""
/* ── Header bar — Gold brand strip ─────────────────── */
QFrame#header {{
    background-color: {COLOR_GOLD};
    border: none;
}}
QLabel#app-title {{
    color: {COLOR_TEXT};
    font-size: 18px;
    font-weight: 700;
    background: transparent;
    letter-spacing: 0.5px;
}}
QLabel#app-subtitle {{
    color: rgba(62, 53, 47, 0.7);
    font-size: 12px;
    background: transparent;
}}
QLabel#header-logo {{
    background: transparent;
}}
"""
