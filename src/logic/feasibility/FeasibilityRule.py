from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from src.logic.feasibility.FeasibilityContext import FeasibilityContext


class FeasibilityRule(ABC):
    """One conservative preflight check before the scheduler backtracks."""

    @abstractmethod
    def validate(self, context: FeasibilityContext) -> List[str]:
        pass
