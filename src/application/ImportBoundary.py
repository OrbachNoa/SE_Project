"""Data structures defining the boundary for import operations."""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional

from src.application.errors.ErrorModel import AppErrorInfo

class ImportMode(Enum):
    """Whether an import replaces existing data or merges on top of it."""

    REPLACE = "REPLACE"
    UPDATE = "UPDATE"

@dataclass
class ImportResult:
    """Outcome of importing one file: success flag, count, and any errors.

    ``errors`` stays a plain ``List[str]`` for backward compatibility with the
    GUI and existing tests. ``error_details`` is the richer, structured form
    (one :class:`AppErrorInfo` per problem) for callers that want category /
    severity / a stable code — it is optional and parallels ``errors``.
    """

    success: bool
    loaded_count: int = 0
    errors: List[str] = field(default_factory=list)
    error_details: List[AppErrorInfo] = field(default_factory=list)

    def has_errors(self) -> bool:
        """True when any error message was recorded."""
        return len(self.errors) > 0

    @classmethod
    def failure(cls, info: AppErrorInfo) -> "ImportResult":
        """Build a failed result from a single structured error.

        Keeps ``errors`` (the user message) and ``error_details`` (the full
        record) in sync so old and new consumers both work.
        """
        return cls(
            success=False,
            loaded_count=0,
            errors=[info.user_message],
            error_details=[info],
        )
