from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set

from src.logic.SlotBuilder import Slot
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig


@dataclass(frozen=True)
class FeasibilityContext:
    """Read-only inputs shared by all preflight feasibility rules and checkers."""

    selected_programs: Optional[list]
    slots: List[Slot]
    config: Optional[ConstraintsConfig]

    @property
    def selected_set(self) -> Optional[Set[str]]:
        return set(self.selected_programs) if self.selected_programs else None
