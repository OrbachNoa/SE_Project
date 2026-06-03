# region Imports
from .FileParser import FileParser
# endregion

class ProgramsFileParser(FileParser):
    """Parses selected program IDs from the programs file."""

    def parse(self, file_path):
        """Reads the programs file and returns selected program IDs."""
        # Start with an empty list, so empty files return no programs.
        programs = []
        # Read the programs file, so selected IDs can be parsed.
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read().strip()
            # Return an empty list when the file has no content.
            if not content:
                return programs

            try:
                FileParser.validateSeparator(content, separator=",")
            except ValueError:
                if len(content) != 5:
                    raise ValueError("Programs file must contain comma-separated IDs, or a single valid 5-digit ID.")
            # Split by commas, so each token can be validated as one program ID.
            parts = [p.strip() for p in content.split(',')]

            # Track seen IDs, so duplicate selections are ignored.
            seen = set()
            for part in parts:
                if part:
                    prog_id = part

                    # Reject newlines inside an ID, so the file uses comma separators.
                    if '\n' in prog_id or '\r' in prog_id:
                        raise ValueError(
                            f"Program IDs must be separated by commas on a single line, "
                            f"not by newlines. Got: '{prog_id.strip()}'. "
                            f"Expected format: 83101, 83102, 83103"
                        )

                    # Validate the program ID, so it matches the expected five-digit format.
                    if len(prog_id) != 5 or not prog_id.isdigit():
                        raise ValueError(f"Program ID must be exactly 5 digits, got: '{prog_id}'")

                    # Skip duplicate IDs, so the same program is selected only once.
                    if prog_id in seen:
                        continue
                    seen.add(prog_id)

                    # Add the valid program ID to the selected programs list.
                    programs.append(prog_id)

        # Return all selected program IDs.
        return programs
