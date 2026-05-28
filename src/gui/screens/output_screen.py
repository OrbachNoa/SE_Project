from PyQt6.QtWidgets import QLabel, QVBoxLayout
from PyQt6.QtCore import Qt
from src.gui.screen import Screen


class OutputScreen(Screen):
    """Output screen skeleton — full UI in SCRUM-137."""

    def __init__(self, controller, router) -> None:
        super().__init__()
        self._controller = controller
        self._router = router
        layout = QVBoxLayout(self)
        label = QLabel("Output Screen — SCRUM-137")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

    def on_enter(self) -> None:
        pass

    def on_leave(self) -> None:
        pass