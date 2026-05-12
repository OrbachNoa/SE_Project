from abc import ABC, abstractmethod

"""
This is the base class for all file parsers.
"""

class FileParser(ABC):

    @abstractmethod
    def parse(self, file_path):
        """
        Parse the file and return the data.
        """
        pass

    def _validate_separator(self, line):
        """
        Validate the file separator.
        """
        return line.strip() == "$$$$"