from .inputValidator import InputValidator

class MaxProgramsValidator(InputValidator):

    MAX_PROGRAMS = 5

    def validate(self, selected_programs):

        if len(selected_programs) > self.MAX_PROGRAMS:
            raise ValueError(f"Maximum {self.MAX_PROGRAMS} programs allowed")