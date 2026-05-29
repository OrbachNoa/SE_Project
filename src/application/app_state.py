"""AppState - the single source of truth for all runtime data.

A thin composite: it holds the two focused sub-states
and exposes them, but contains no parsing, scheduling, or persistence logic
itself. Splitting input state from result state keeps each focused, reduces
coupling, and preserves single-responsibility.
Everything mutating state goes through the sub-states' own methods.
"""
from __future__ import annotations

from src.application.input_data_state import InputDataState
from src.application.schedule_result_state import ScheduleResultState


class AppState:
    """Holds the input-data state and the schedule-result state."""

    def __init__(self) -> None:
        self._input_state = InputDataState()
        self._schedule_state = ScheduleResultState()

    # ---- Getters for the sub-states. No setters, as all mutation should go through the sub-states' own methods ----
    
    def get_input_state(self) -> InputDataState:
        """Return the input-data sub-state (loaded courses and periods)."""
        return self._input_state

    def get_schedule_state(self) -> ScheduleResultState:
        """Return the schedule-result sub-state (generated schedules)."""
        return self._schedule_state