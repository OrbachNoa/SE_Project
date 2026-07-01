from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.logic.feasibility.FeasibilityContext import FeasibilityContext


class FeasibilityRule(ABC):
    """Base class for checks that run before the scheduler starts."""

    @abstractmethod
    def validate(self, context: FeasibilityContext) -> List[str]:
        """Return problem messages, or an empty list if everything is ok."""
        pass
