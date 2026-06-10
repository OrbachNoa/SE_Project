from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from gui.core.ScreenRouter import ScreenRouter
from gui.features.input.InputScreen import InputScreen
from gui.features.output.OutputScreen import OutputScreen
from gui.core.styles.Theme import APP_STYLESHEET
from gui.core.styles.DialogStyles import DIALOG_STYLESHEET

# Simple names used to identify the different screens in our app
SCREEN_INPUT  = "input"
SCREEN_OUTPUT = "output"

# This is the main window of the application that holds everything together
class App(QMainWindow):
    def __init__(self, controller) -> None:
        """Initialize the main window."""
        super().__init__()
        
        # Save a reference to the main brain (controller) of the app
        self._controller = controller
        
        # Set the window's title, default starting size, and the minimum size it can be shrunk to
        self.setWindowTitle("Exam Scheduler v2.0")
        self.resize(1100, 720)
        self.setMinimumSize(800, 560)
        
        # Apply our custom visual designs (CSS-like styles) to the whole window
        self.setStyleSheet(APP_STYLESHEET + DIALOG_STYLESHEET)

        # Create a "stack" container. Think of it like a deck of cards where only one screen is visible at a time
        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)
        
        # Set up the router, which is responsible for switching between the different screens
        self._router = ScreenRouter(self._stack)
        
        # Add our two main screens (Input and Output) to the router's memory
        self._router.register(SCREEN_INPUT,  InputScreen(controller, self._router))
        self._router.register(SCREEN_OUTPUT, OutputScreen(controller, self._router))
        
        # Decide which screen the user should see first when the app opens
        self._router.show(SCREEN_INPUT)

    # This function is triggered automatically when the user clicks the 'X' button to close the window
    def closeEvent(self, event) -> None:
        """Handle application close event by notifying the controller. """
        # Tell the background controller to safely wrap up and stop any running processes
        self._controller.on_app_closing()
        
        # Allow the window to actually close
        event.accept()

    # A simple command to actually display the window on the user's screen
    def start(self) -> None:
        """Display the main window. """
        self.show()