from .inputValidator import InputValidator
from data.programs import programs_data

class ProgramExistenceValidator(InputValidator):

    def __init__(self, master=None):
        # Frozen at construction time — explicit dependency, no hidden state.
        self._valid_ids = set(master) if master is not None else set(programs_data.keys())

    def validate(self, selected_programs, master=None):
        # Checks if all selected IDs exist using the stored set to ensure highly efficient lookups.
        valid_ids = set(master) if master is not None else self._valid_ids
        return all(p_id in valid_ids for p_id in selected_programs)