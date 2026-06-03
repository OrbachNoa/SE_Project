# region Imports
from abc import ABC, abstractmethod
from .validationResult import ValidationResult
# endregion

class IInputValidator(ABC):
    """
    Defines the abstract base class for input validators.
    """

    @abstractmethod
    def validate(self, selected, master=None) -> bool:
        """
        Returns True when the selected input is valid.
        """
        pass

    def error_message(self, selected) -> str:
        """
        Returns a readable validation error message.
        """
        return f"Validation failed in {type(self).__name__}"
    
    def validate_as_result(self, selected) -> ValidationResult:
        """
        Validate the input and return a ValidationResult object.
        This method is a wrapper around the validate method.
        """
        result = ValidationResult()
        if not self.validate(selected):
            result.add_error(self.error_message(selected))
        return result