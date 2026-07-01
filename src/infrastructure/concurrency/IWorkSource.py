"""Interface for objects that give worker processes their next WorkUnit."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.logic.parallel.WorkUnit import WorkUnit


class IWorkSource(ABC):
    """Common interface for pulling work units during the search."""

    @abstractmethod
    def get_next(self) -> Optional[WorkUnit]:
        """Return the next WorkUnit, or None when this worker should stop."""
        raise NotImplementedError
