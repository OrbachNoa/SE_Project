from abc import ABC, abstractmethod

class InputValidator(ABC):
    """Defines the shared interface for input validators."""

    @abstractmethod
    def validate(self, selected, master=None) -> bool:
        """Returns True when the selected input is valid."""
        pass

    def error_message(self, selected) -> str:
        """Returns a readable validation error message."""
        return f"Validation failed in {type(self).__name__}"
