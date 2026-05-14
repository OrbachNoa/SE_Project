from abc import ABC, abstractmethod

"""
This is the base class for all input validators.
"""

class InputValidator(ABC):

    @abstractmethod
    def validate(self, selected, master=None) -> bool:
        """Validate the input data."""
        pass