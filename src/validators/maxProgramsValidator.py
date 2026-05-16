from .inputValidator import InputValidator

class MaxProgramsValidator(InputValidator):
    MAX_PROGRAMS = 5

    def validate(self, selected_programs, master=None) -> bool:
        if not selected_programs:
            return False
        if len(selected_programs) > self.MAX_PROGRAMS:
            return False
        return True

    def error_message(self, selected_programs) -> str:
        if not selected_programs:
            return "At least one program must be selected in the programs file."
        return (
            f"Too many programs selected: {len(selected_programs)}. "
            f"Maximum is {self.MAX_PROGRAMS}."
        )