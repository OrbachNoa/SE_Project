"""Defines the observer interface for the scheduling engine.

This interface exists because the core Scheduler needs a way to stream updates 
without knowing anything about queues, threads, or GUIs.
"""
from __future__ import annotations
from abc import ABC, abstractmethod

class IScheduleObserver(ABC):
    """Listens to the scheduler because we need to stream live updates to the user."""

    @abstractmethod
    def on_schedule_found(self, schedule) -> None:
        """Called when a valid schedule is found because we want to show it immediately."""
        raise NotImplementedError

    @abstractmethod
    def on_progress(self, value: int) -> None:
        """Called to report progress because the GUI needs to update the progress bar."""
        raise NotImplementedError

    @abstractmethod
    def should_cancel(self) -> bool:
        """Checks if the user clicked cancel because we want to stop the heavy CPU work."""
        raise NotImplementedError

    @abstractmethod
    def on_finished(self) -> None:
        """Called when the search is fully complete because the system needs to close resources."""
        raise NotImplementedError

    @abstractmethod
    def on_error(self, message: str) -> None:
        """Called when a fatal error occurs because we want to prevent a silent crash."""
        raise NotImplementedError