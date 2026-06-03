from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from gui.ScreenRouter import ScreenRouter
from gui.screens.InputScreen import InputScreen
from gui.screens.OutputScreen import OutputScreen

SCREEN_INPUT  = "input"
SCREEN_OUTPUT = "output"

APP_STYLESHEET = """
/* ── Base ─────────────────────────────────────────────────────────── */
QWidget {
    background-color: #f1f5f9;
    color: #1e293b;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ── Header bar ───────────────────────────────────────────────────── */
QFrame#header {
    background-color: #0f172a;
    border: none;
}
QLabel#app-title {
    color: #f8fafc;
    font-size: 20px;
    font-weight: 700;
    background: transparent;
    letter-spacing: 0.5px;
}
QLabel#app-subtitle {
    color: #94a3b8;
    font-size: 12px;
    background: transparent;
}

/* ── Cards ────────────────────────────────────────────────────────── */
QFrame#card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QLabel#card-title {
    color: #0f172a;
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}
QLabel#card-hint {
    color: #94a3b8;
    font-size: 11px;
    background: transparent;
}

/* ── Status pills ─────────────────────────────────────────────────── */
QLabel#status-ok {
    color: #16a34a;
    font-size: 12px;
    font-weight: 600;
    background: transparent;
}
QLabel#status-pending {
    color: #94a3b8;
    font-size: 12px;
    background: transparent;
}
QLabel#status-warning {
    color: #d97706;
    font-size: 12px;
    background: transparent;
}
QLabel#status-error {
    color: #dc2626;
    font-size: 12px;
    background: transparent;
}

/* ── Buttons ──────────────────────────────────────────────────────── */
QPushButton {
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
    outline: none;
}
QPushButton#btn-primary {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    font-size: 14px;
    font-weight: 600;
    padding: 11px 24px;
}
QPushButton#btn-primary:hover {
    background-color: #1d4ed8;
}
QPushButton#btn-primary:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
}
QPushButton#btn-secondary {
    background-color: #ffffff;
    color: #374151;
    border: 1px solid #d1d5db;
}
QPushButton#btn-secondary:hover {
    background-color: #f9fafb;
    border-color: #9ca3af;
}
QPushButton#btn-secondary:disabled {
    color: #cbd5e1;
    border-color: #e5e7eb;
}
QPushButton#btn-danger {
    background-color: #ffffff;
    color: #dc2626;
    border: 1px solid #fca5a5;
}
QPushButton#btn-danger:hover {
    background-color: #fef2f2;
    border-color: #f87171;
}
QPushButton#btn-ghost {
    background-color: transparent;
    color: #64748b;
    border: none;
    font-size: 13px;
}
QPushButton#btn-ghost:hover {
    color: #0f172a;
    background-color: #f1f5f9;
}

/* ── Radio buttons ────────────────────────────────────────────────── */
QRadioButton {
    background: transparent;
    color: #374151;
    spacing: 6px;
}
QRadioButton::indicator {
    width: 15px;
    height: 15px;
    border-radius: 8px;
    border: 2px solid #cbd5e1;
    background: #ffffff;
}
QRadioButton::indicator:checked {
    border-color: #2563eb;
    background: #2563eb;
}

/* ── Progress bar ─────────────────────────────────────────────────── */
QProgressBar {
    background-color: #e2e8f0;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 4px;
}

/* ── Divider ──────────────────────────────────────────────────────── */
QFrame#divider {
    background-color: #e2e8f0;
    border: none;
    max-height: 1px;
}

/* ── Nav bar (output screen) ──────────────────────────────────────── */
QFrame#nav-bar {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}
QLabel#counter-label {
    color: #374151;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
    min-width: 120px;
}

/* ── Content area ─────────────────────────────────────────────────── */
QFrame#content-area {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QLabel#content-placeholder {
    color: #94a3b8;
    font-size: 14px;
    background: transparent;
}
QLabel#schedule-text {
    color: #1e293b;
    font-size: 12px;
    font-family: "Consolas", "Courier New", monospace;
    background: transparent;
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