from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from gui.core.ScreenRouter import ScreenRouter
from gui.features.input.InputScreen import InputScreen
from gui.features.output.OutputScreen import OutputScreen
from gui.core.styles.Theme import APP_STYLESHEET
from gui.core.styles.DialogStyles import DIALOG_STYLESHEET

# Define screen constants
SCREEN_INPUT  = "input"
SCREEN_OUTPUT = "output"

# Main application window
class App(QMainWindow):
    def __init__(self, controller) -> None:
        """Initialize the main window."""
        super().__init__()
        self._controller = controller
        self.setWindowTitle("Exam Scheduler v2.0")
        self.resize(1100, 720)
        self.setMinimumSize(800, 560)
        self.setStyleSheet(APP_STYLESHEET + DIALOG_STYLESHEET)

        # Create stacked widget and set as central widget
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        self._router = ScreenRouter(self._stack)
        self._router.register(SCREEN_INPUT,  InputScreen(controller, self._router))
        self._router.register(SCREEN_OUTPUT, OutputScreen(controller, self._router))
        self._router.show(SCREEN_INPUT)

    def closeEvent(self, event) -> None:
        """Handle application close event by notifying the controller. """
        self._controller.on_app_closing()
        event.accept()

    def start(self) -> None:
        """Display the main window. """
        self.show()