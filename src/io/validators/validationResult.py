from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ValidationResult:
    """Holds the outcome of a validation process including status and a list of error messages."""

    is_valid: bool = True
    errors: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Appends the given error message to the list and marks the validation as failed."""
        self.errors.append(message)
        self.is_valid = False

    def merge(self, other: "ValidationResult") -> None:
        """Merges all errors from another validation result directly into this one."""
        for error in other.errors:
            self.add_error(error)

    def __repr__(self) -> str:
        status = "valid" if self.is_valid else f"invalid ({len(self.errors)} error(s))"
        return f"ValidationResult({status})"