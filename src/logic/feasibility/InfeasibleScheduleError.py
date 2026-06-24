from __future__ import annotations

from typing import List


class InfeasibleScheduleError(Exception):
    """Raised when the input cannot lead to any valid schedule."""

    def __init__(self, errors: List[str]) -> None:
        # Build one clear error message from all feasibility problems.
        super().__init__("No valid schedules possible:\n- " + "\n- ".join(errors))
        # Keep the original list so the UI or tests can read each problem separately.
        self.errors = errors
