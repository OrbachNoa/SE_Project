from __future__ import annotations

from typing import Any, Dict, List, Type

from src.parsers.fileParser import FileParser
from src.parsers.courseParser import CoursesFileParser
from src.parsers.dateParser import ExamPeriodsFileParser
from src.parsers.programParser import ProgramsFileParser


class ParserFactory:
    """Creates concrete FileParser instances based on a registered file-type key."""

    _REGISTRY: Dict[str, Type[FileParser]] = {
        "courses": CoursesFileParser,
        "periods": ExamPeriodsFileParser,
        "programs": ProgramsFileParser,
    }

    @classmethod
    def create(cls, file_type: str, *parser_values: Any, **parser_config: Any) -> FileParser:
        """Returns a new instance of the requested parser type, passing any optional arguments to its constructor."""
        
        # Attempt to fetch the parser class from the registry
        parser_cls = cls._REGISTRY.get(file_type)
        
        # If the file type is not registered, raise a descriptive error
        if parser_cls is None:
            supported = ", ".join(sorted(cls._REGISTRY))
            raise ValueError(
                f"Unknown file type '{file_type}'. "
                f"Supported types: {supported}."
            )
            
        # Instantiate and return the requested parser with dynamic arguments
        return parser_cls(*parser_values, **parser_config)

    @classmethod
    def supported_types(cls) -> List[str]:
        """Returns a sorted list of all currently registered file-type keys."""
        return sorted(cls._REGISTRY)

    @classmethod
    def register(cls, file_type: str, parser_cls: Type[FileParser]) -> None:
        """Registers a new parser class under a given file type key to extend supported formats dynamically."""
        
        # Prevent overwriting an existing parser registration
        if file_type in cls._REGISTRY:
            raise ValueError(
                f"File type '{file_type}' is already registered "
                f"(registered class: {cls._REGISTRY[file_type].__name__})."
            )
            
        # Add the new parser class to the registry
        cls._REGISTRY[file_type] = parser_cls