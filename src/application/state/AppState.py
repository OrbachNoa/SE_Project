"""AppState - the single source of truth for all runtime data.

A thin composite: it holds the two focused sub-states
and exposes them, but contains no parsing, scheduling, or persistence logic
itself. Splitting input state from result state keeps each focused, reduces
coupling, and preserves single-responsibility.
Everything mutating state goes through the sub-states' own methods.
"""
from __future__ import annotations

from typing import Optional

from application.state.InputDataState import InputDataState
from application.state.ScheduleResultState import ScheduleResultState


class AppState:
    """Holds the input-data state and the schedule-result state.

    `schedule_state` is injectable so the composition root can supply a
    HybridScheduleResultState (SQLite overflow + paged navigation) without
    modifying this class. When omitted, a plain ScheduleResultState is
    created — preserving full backward compatibility.
    """

    def __init__(
        self,
        schedule_state: Optional[ScheduleResultState] = None,
    ) -> None:
        # Allocates a dedicated local buffer for holding incoming raw file parameters
        self._input_state = InputDataState()
        
        # Injects the target processing storage layer or defaults to a standard runtime memory tracker
        self._schedule_state = (
            schedule_state if schedule_state is not None else ScheduleResultState()
        )

    # ---- Getters for the sub-states. No setters, as all mutation should go through the sub-states' own methods ----

    def get_input_state(self) -> InputDataState:
        """Return the input-data sub-state containing loaded academic courses and periods profiles."""
        return self._input_state

    def get_schedule_state(self) -> ScheduleResultState:
        """Return the schedule-result sub-state managing compiled background engine output nodes."""
        return self._schedule_state