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

    @staticmethod
    def validateSeparator(content):
        """Validate the file separator."""
        if "$$$$" not in content:
            raise ValueError("Separator $$$$ not found.")
        return True