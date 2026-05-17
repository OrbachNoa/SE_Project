from .inputValidator import InputValidator
from data.programs import programs_data

class ProgramExistenceValidator(InputValidator):

    def __init__(self, master=None):
        self._valid_ids = set(master) if master is not None else set(programs_data.keys())

    def validate(self, selected_programs, master=None) -> bool:
        valid_ids = set(master) if master is not None else self._valid_ids
        return all(p_id in valid_ids for p_id in selected_programs)

    def error_message(self, selected_programs) -> str:
        invalid = [p for p in selected_programs if p not in self._valid_ids]
        return (
            f"Unknown program code(s): {invalid}. "
            f"Valid codes are: {sorted(self._valid_ids)}"
        )