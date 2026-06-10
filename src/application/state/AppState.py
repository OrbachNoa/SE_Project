from __future__ import annotations

from typing import Optional

from src.application.state.InputDataState import InputDataState
from src.application.state.ScheduleResultState import ScheduleResultState


class AppState:
    """Holds two focused sub-states: the input-data state and the schedule-result state.

    schedule_state is injectable so the composition root can supply a
    HybridScheduleResultState (SQLite overflow + paged navigation) without
    modifying this class. When omitted, a plain ScheduleResultState is
    created — preserving full backward compatibility.
    """

    def __init__(
        self,
        schedule_state: Optional[ScheduleResultState] = None,
    ) -> None:
        # Holds loaded courses and exam periods.
        self._input_state = InputDataState()
        
        # Use the injected state if provided, otherwise default to in-memory only.
        self._schedule_state = (
            schedule_state if schedule_state is not None else ScheduleResultState()
        )

    # Getters for the sub-states. No setters, as all mutation should go through the sub-states' own methods

    def get_input_state(self) -> InputDataState:
        """Return the input-data sub-state (courses and exam periods)."""
        return self._input_state

    def get_schedule_state(self) -> ScheduleResultState:
        """Return the schedule-result sub-state (generated schedules)."""
        return self._schedule_state
