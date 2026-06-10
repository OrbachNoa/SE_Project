from PyQt6.QtWidgets import QWidget

# This is a "blueprint" or "template" class for all the different screens in our app.
# We use this so every screen is forced to follow the same basic rules.
class Screen(QWidget):
    """
    Base class for every application screen.
    Does NOT use ABC — PyQt6 metaclass conflicts with ABCMeta.
    Abstract behaviour enforced via NotImplementedError.
    """

    # The standard setup function that prepares this widget to be displayed on the screen
    def __init__(self, parent=None):
        super().__init__(parent)

    # A strict rule: Any specific screen we create MUST write its own version of this function
    # to decide what happens exactly when the user enters or opens that screen.
    def on_enter(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement on_enter()")

    # Another strict rule: Any specific screen MUST write its own version of this function
    # to clean things up, stop processes, or save data when the user leaves that screen.
    def on_leave(self) -> None:
        raise NotImplementedError(f"{type(self).__name__} must implement on_leave()")