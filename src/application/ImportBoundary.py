"""Data structures defining the boundary for import operations."""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import List

class ImportMode(Enum):
    """Whether an import replaces existing data or merges on top of it."""

    REPLACE = "REPLACE"
    UPDATE = "UPDATE"

@dataclass
class ImportRequest:
    """Bundles the inputs the facade needs to import one file."""

    path: str
    file_type: str
    mode: ImportMode

@dataclass
class ImportResult:
    """Outcome of importing one file: success flag, count, and any errors."""

    success: bool
    loaded_count: int = 0
    errors: List[str] = field(default_factory=list)

    def has_errors(self) -> bool:
        """True when any error message was recorded."""
        return len(self.errors) > 0
