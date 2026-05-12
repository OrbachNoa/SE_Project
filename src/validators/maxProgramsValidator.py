from .inputValidator import InputValidator

class MaxProgramsValidator(InputValidator):

    MAX_PROGRAMS = 5

    def validate(self, selected_programs, master=None):
        if not selected_programs:
            return False
        if len(selected_programs) > self.MAX_PROGRAMS:
            return False
        return True