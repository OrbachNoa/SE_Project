"""Result of a file-import operation, returned to the caller."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ImportResult:
    """Outcome of importing one file: success flag, count, and any errors."""

    success: bool
    loaded_count: int = 0
    errors: List[str] = field(default_factory=list)

    def has_errors(self) -> bool:
        """True when any error message was recorded."""
        return len(self.errors) > 0