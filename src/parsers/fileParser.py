# region Imports
from abc import ABC, abstractmethod
# endregion

class FileParser(ABC):
    """
    Abstract base class for all file parsers.
    """

    @abstractmethod
    def parse(self, file_path):
        """
        Parse the file and return the data.
        """
        pass

    @staticmethod
    def validateSeparator(content):
        """
        Validates the file separator.
        """
        if "$$$$" not in content:
            raise ValueError("Separator $$$$ not found.")
        return True