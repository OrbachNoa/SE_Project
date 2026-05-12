from .fileParser import FileParser
from typing import override

"""
This is the program parser class.
"""
class ProgramParser(FileParser):

    def parse(self, file_path):
        """
        Parse the file and return the data.
        """
        # Init list to store programs
        programs = []
        # Open the file
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read().strip()
            # If the file is empty, return an empty list
            if not content:
                return programs
                
            # Split the file content by commas
            parts = [p.strip() for p in content.split(',')]
            
            # Iterate over all parts
            for part in parts:
                # If the part is not empty
                if part:
                    # Try to convert the part to an integer
                    try:
                        prog_id = int(part)
                    # If the part is not an integer, raise a ValueError
                    except ValueError:
                        raise ValueError(f"Invalid program ID format: {part}")
                        
                    # Check if the program ID is exactly 5 digits
                    if len(str(prog_id)) != 5:
                        raise ValueError(f"Program ID must be 5 digits: {prog_id}")
                    
                    programs.append(prog_id)
                        
        return programs

    @override
    def _validate_separator(self, line):
        """
        Override since the programs file uses commas as separators in this file, not $$$$
        """
        return "," in line