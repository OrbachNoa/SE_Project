from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from gui.ScreenRouter import ScreenRouter
from gui.screens.InputScreen import InputScreen
from gui.screens.OutputScreen import OutputScreen

SCREEN_INPUT  = "input"
SCREEN_OUTPUT = "output"

APP_STYLESHEET = """
/* ── Base widget defaults ─────────────────────────────────────────── */
QWidget {
    background-color: #FDFBF7;
    color: #3E352F;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ── Header bar — Gold brand strip ─────────────────── */
QFrame#header {
    background-color: #d4b483;
    border: none;
}
QLabel#app-title {
    color: #3E352F;
    font-size: 18px;
    font-weight: 700;
    background: transparent;
    letter-spacing: 0.5px;
}
QLabel#app-subtitle {
    color: rgba(62, 53, 47, 0.7);
    font-size: 12px;
    background: transparent;
}

/* ── Cards — white panels with subtle border ──────────────────────── */
QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 4px;
}
QLabel#card-title {
    color: #3E352F;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}
QLabel#card-hint {
    color: #9E948A;
    font-size: 11px;
    background: transparent;
}

/* ── Status pills — inline state indicators ───────────────────────── */
QLabel#status-ok {
    color: #16A34A;
    font-size: 12px;
    font-weight: 600;
    background: transparent;
}
QLabel#status-pending {
    color: #9E948A;
    font-size: 12px;
    background: transparent;
}
QLabel#status-warning {
    color: #EA580C;
    font-size: 12px;
    background: transparent;
}
QLabel#status-error {
    color: #DC2626;
    font-size: 12px;
    background: transparent;
}

/* ── Buttons — base reset, then per-variant overrides ─────────────── */
QPushButton {
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    border: none;
    outline: none;
}
QPushButton#btn-primary {
    background-color: #3396ad;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 20px;
}
QPushButton#btn-primary:hover {
    background-color: #297B8F;
}
QPushButton#btn-primary:disabled {
    background-color: #E2E8F0;
    color: #9E948A;
}
QPushButton#btn-secondary {
    background-color: #FFFFFF;
    color: #3E352F;
    border: 1px solid #D5CFC9;
    border-radius: 8px;
    padding: 6px 14px;
}
QPushButton#btn-secondary:hover {
    background-color: #FDFBF7;
    border-color: #3396ad;
}
QPushButton#btn-secondary:disabled {
    color: #D5CFC9;
    border-color: #E2E8F0;
}
QPushButton#btn-danger {
    background-color: #FFFFFF;
    color: #DC2626;
    border: 1px solid #FCA5A5;
}
QPushButton#btn-danger:hover {
    background-color: #FEF2F2;
    border-color: #F87171;
}
QPushButton#btn-ghost {
    background-color: transparent;
    color: #8A7E72;
    border: none;
    font-size: 13px;
}
QPushButton#btn-ghost:hover {
    color: #3396ad;
    background-color: #FDFBF7;
}

/* ── Radio buttons — Teal accent when selected ────────────────── */
QRadioButton {
    background: transparent;
    color: #3E352F;
    spacing: 6px;
}
QRadioButton::indicator {
    width: 15px;
    height: 15px;
    border-radius: 8px;
    border: 2px solid #D5CFC9;
    background: #FFFFFF;
}
QRadioButton::indicator:checked {
    border-color: #3396ad;
    background: #3396ad;
}

/* ── Progress bar — green fill on light track ─────────────────────── */
QProgressBar {
    background-color: #E2E8F0;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #16A34A;
    border-radius: 4px;
}

/* ── Divider — 1 px horizontal separator ─────────────────────────── */
QFrame#divider {
    background-color: #E2E8F0;
    border: none;
    max-height: 1px;
}

/* ── Nav bar (output screen) — top navigation strip ──────────────── */
QFrame#nav-bar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}
QLabel#counter-label {
    color: #3E352F;
    font-size: 14px;
    font-weight: 600;
    background: transparent;
    min-width: 340px;
}

/* ── Content area — main display panel on the output screen ───────── */
QFrame#content-area {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}
QLabel#content-placeholder {
    color: #9E948A;
    font-size: 14px;
    background: transparent;
}
QLabel#schedule-text {
    color: #3E352F;
    font-size: 12px;
    font-family: "Consolas", "Courier New", monospace;
    background: transparent;
}

/* QToolTip must be styled explicitly — without this rule Qt inherits the system
   dark background while keeping the dark text color, producing an unreadable
   black-on-black rectangle. */
QToolTip {
    background-color: #3E352F;
    color: #FDFBF7;
    border: 1px solid #2B2521;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Scroll areas — transparent container, slim styled handle ─────── */
QScrollArea {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    width: 6px;
    background: transparent;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #9E948A;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}

/* ── Group boxes — labelled section containers ────────────────────── */
QGroupBox {
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    margin-top: 8px;
    font-weight: 600;
    color: #3E352F;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}

/* ── Action bar — Load/Generate toolbar below the header ──────────── */
QFrame#action-bar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}

/* ── Info bar — solution metadata strip on the output screen ──────── */
QFrame#info-bar {
    background-color: #FDFBF7;
    border-bottom: 1px solid #E2E8F0;
}

/* ── Status badges — neutral and success variants ─────────────────── */
QLabel#badge {
    background-color: #F1F5F9;
    color: #8A7E72;
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
}
QLabel#badge-ok {
    background-color: #E8F5E9;
    color: #16A34A;
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
}
"""


class App(QMainWindow):
    """Main application window."""

    def __init__(self, controller) -> None:
        super().__init__()
        self._controller = controller
        self.setWindowTitle("Exam Scheduler v2.0")
        self.resize(1100, 720)
        self.setMinimumSize(800, 560)
        self.setStyleSheet(APP_STYLESHEET)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self._router = ScreenRouter(self._stack)
        self._router.register(SCREEN_INPUT,  InputScreen(controller, self._router))
        self._router.register(SCREEN_OUTPUT, OutputScreen(controller, self._router))
        self._router.show(SCREEN_INPUT)

    def closeEvent(self, event) -> None:
        self._controller.on_app_closing()
        event.accept()

    def start(self) -> None:
        self.show()