from PyQt6.QtWidgets import QWidget


class Screen(QWidget):
    """
    Base class for every application screen.
    Does NOT use ABC — PyQt6 metaclass conflicts with ABCMeta.
    Abstract behaviour enforced via NotImplementedError.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def on_enter(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement on_enter()")

    def on_leave(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement on_leave()")