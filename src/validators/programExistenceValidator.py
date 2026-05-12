from .inputValidator import InputValidator
from data.programs import programs_data

"""
Validates the selected programs
"""
class ProgramExistenceValidator(InputValidator):

    def validate(self, selected_programs):

        for program in selected_programs:

            if program not in programs_data.keys():
                raise ValueError(
                    f"Program does not exist: {program}"
                )   