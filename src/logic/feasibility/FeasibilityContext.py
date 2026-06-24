from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set

from src.logic.SlotBuilder import Slot
from src.logic.checkers.config.ConstraintsConfig import ConstraintsConfig

# Keep this context read-only after it is created.
@dataclass(frozen=True)
class FeasibilityContext:
    """Small read-only object that keeps the data needed for feasibility checks."""

    # Programs chosen by the user.
    # None means there is no program filter.
    selected_programs: Optional[list]
    # Slots that were created from the selected courses and exam periods.
    slots: List[Slot]
    # Optional rule settings used by the feasibility checks.
    config: Optional[ConstraintsConfig]

    @property
    def selected_set(self) -> Optional[Set[str]]:
        """Return the selected programs as a set for faster lookup."""

        # Empty selection is treated like no selected-program filter.
        return set(self.selected_programs) if self.selected_programs else None
