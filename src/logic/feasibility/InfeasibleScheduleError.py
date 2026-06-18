from __future__ import annotations

from typing import List


class InfeasibleScheduleError(Exception):
    """Raised when preflight feasibility checks prove no schedule can satisfy
    the constraints. Carries only a list of plain strings so it stays cheap
    to construct and safe to forward across process/IPC boundaries if needed.
    """

    def __init__(self, errors: List[str]) -> None:
        super().__init__("No valid schedules possible:\n- " + "\n- ".join(errors))
        self.errors = errors
