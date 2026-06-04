from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from gui.ScreenRouter import ScreenRouter
from gui.screens.InputScreen import InputScreen
from gui.screens.OutputScreen import OutputScreen

SCREEN_INPUT  = "input"
SCREEN_OUTPUT = "output"

APP_STYLESHEET = """
/* ── Base widget defaults ─────────────────────────────────────────── */
QWidget {
    background-color: #FAFAFA;
    color: #143D30;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ── Header bar — dark green Bar-Ilan brand strip ─────────────────── */
QFrame#header {
    background-color: #143D30;
    border: none;
}
QLabel#app-title {
    color: #F8FAFC;
    font-size: 18px;
    font-weight: 700;
    background: transparent;
    letter-spacing: 0.5px;
}
QLabel#app-subtitle {
    color: rgba(255, 255, 255, 0.55);
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
    color: #143D30;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}
QLabel#card-hint {
    color: #94A3B8;
    font-size: 11px;
    background: transparent;
}

/* ── Status pills — inline state indicators ───────────────────────── */
QLabel#status-ok {
    color: #14633F;
    font-size: 12px;
    font-weight: 600;
    background: transparent;
}
QLabel#status-pending {
    color: #94A3B8;
    font-size: 12px;
    background: transparent;
}
QLabel#status-warning {
    color: #D97706;
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
    background-color: #14633F;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    padding: 10px 20px;
}
QPushButton#btn-primary:hover {
    background-color: #0F2D23;
}
QPushButton#btn-primary:disabled {
    background-color: #E2E8F0;
    color: #94A3B8;
}
QPushButton#btn-secondary {
    background-color: #FFFFFF;
    color: #143D30;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px 14px;
}
QPushButton#btn-secondary:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
}
QPushButton#btn-secondary:disabled {
    color: #CBD5E1;
    border-color: #E5E7EB;
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
    color: #64748B;
    border: none;
    font-size: 13px;
}
QPushButton#btn-ghost:hover {
    color: #143D30;
    background-color: #F1F5F9;
}

/* ── Radio buttons — sky-blue accent when selected ────────────────── */
QRadioButton {
    background: transparent;
    color: #374151;
    spacing: 6px;
}
QRadioButton::indicator {
    width: 15px;
    height: 15px;
    border-radius: 8px;
    border: 2px solid #CBD5E1;
    background: #FFFFFF;
}
QRadioButton::indicator:checked {
    border-color: #3E89BD;
    background: #3E89BD;
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
    background-color: #14633F;
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
    color: #143D30;
    font-size: 14px;
    font-weight: 600;
    background: transparent;
    min-width: 140px;
}

/* ── Content area — main display panel on the output screen ───────── */
QFrame#content-area {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}
QLabel#content-placeholder {
    color: #94A3B8;
    font-size: 14px;
    background: transparent;
}
QLabel#schedule-text {
    color: #143D30;
    font-size: 12px;
    font-family: "Consolas", "Courier New", monospace;
    background: transparent;
}

/* QToolTip must be styled explicitly — without this rule Qt inherits the system
   dark background while keeping the dark text color, producing an unreadable
   black-on-black rectangle. */
QToolTip {
    background-color: #143D30;
    color: #F8FAFC;
    border: 1px solid #0F2D23;
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
    background: #94A3B8;
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
    color: #143D30;
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
    background-color: #F8FAFC;
    border-bottom: 1px solid #E2E8F0;
}

/* ── Status badges — neutral and success variants ─────────────────── */
QLabel#badge {
    background-color: #F1F5F9;
    color: #64748B;
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 11px;
}
QLabel#badge-ok {
    background-color: #E5F0EB;
    color: #14633F;
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