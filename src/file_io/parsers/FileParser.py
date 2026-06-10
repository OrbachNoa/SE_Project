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
    def validateSeparator(content, separator="$$$$"):
        """
        Validates the file separator.
        """
        if separator not in content:
            raise ValueError(f"Separator '{separator}' not found.")
        return True