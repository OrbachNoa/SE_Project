from .fileParser import FileParser
from typing import override
from ..models.course import ProgramEntry

"""
This is the program parser class.
"""
class ProgramsFileParser(FileParser):

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
                if part:
                    # Keep as string for tests
                    prog_id = part
                    
                    # Check if the program id is 5 digits
                    if len(prog_id) != 5 or not prog_id.isdigit():
                        raise ValueError(f"Program ID must be 5 digits: {prog_id}")
                    
                    # Add the program to the list in ProgramEntry object
                    # For tests, the other values are default
                    programs.append(ProgramEntry(program_id=prog_id, year=0, semester=None, requirement=None))
        
        # Return the list of programs
        return programs

    @override
    def _validate_separator(self, line):
        """
        Override since the programs file uses commas as separators in this file, not $$$$
        """
        return "," in line