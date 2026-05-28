import sys
from PyQt6.QtWidgets import QApplication
from src.gui.app import App
from src.application.app_controller import AppController


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AppController()
    window = App(controller)
    window.start()
    sys.exit(app.exec())