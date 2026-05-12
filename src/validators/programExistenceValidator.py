from .inputValidator import InputValidator
from data.programs import programs_data

"""
Validates the selected programs
"""
class ProgramExistenceValidator(InputValidator):

    def validate(self, selected_programs, master=None):
        for program in selected_programs:
            if master is None:
                if program.programId not in programs_data.keys():
                    return False
            else:
                if program.programId not in master:
                    return False
        return True