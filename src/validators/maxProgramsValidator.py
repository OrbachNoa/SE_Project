# region Imports
from .inputValidator import InputValidator
# endregion

class MaxProgramsValidator(InputValidator):
    """
    Validates that the number of selected programs does not exceed the maximum allowed.
    """

    # Maximum number of programs that can be selected.
    MAX_PROGRAMS = 5

    def validate(self, selected_programs, master=None) -> bool:
        """
        Validate that the number of selected programs does not exceed the maximum allowed or is less than needed.
        """
        if not selected_programs:
            return False
        if len(selected_programs) > self.MAX_PROGRAMS:
            return False
        return True

    def error_message(self, selected_programs) -> str:
        """
        Returns an error message if the validation fails.
        """
        if not selected_programs:
            return "At least one program must be selected in the programs file."
        return (
            f"Too many programs selected: {len(selected_programs)}. "
            f"Maximum is {self.MAX_PROGRAMS}."
        )