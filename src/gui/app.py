from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from src.gui.screen_router import ScreenRouter
from src.gui.screens.input_screen import InputScreen
from src.gui.screens.output_screen import OutputScreen

SCREEN_INPUT  = "input"
SCREEN_OUTPUT = "output"


class App(QMainWindow):
    """Main application window."""

    def __init__(self, controller) -> None:
        super().__init__()
        self._controller = controller
        self.setWindowTitle("Exam Scheduler v2.0")
        self.resize(1100, 720)
        self.setMinimumSize(800, 560)
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