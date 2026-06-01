"""AppController - thin controller between the GUI and the ApplicationFacade.

Holds an injected ApplicationFacade and forwards each user action to it.
Contains no logic of its own: screens call the controller, the controller calls
the facade.
"""
from __future__ import annotations

from typing import List

from src.application.application_facade import ApplicationFacade
from src.application.import_request import ImportRequest
from src.application.import_mode import ImportMode
from src.application.import_result import ImportResult
from src.application.dto_viewmodel.schedule_view_model import ScheduleViewModel
from src.concurrency.SchedulerWorker import SchedulerWorker


class AppController:
    """Forwards GUI actions to the ApplicationFacade."""

    def __init__(self, facade: ApplicationFacade) -> None:
        self._facade = facade

    def load_file(self, path: str, file_type: str, mode: ImportMode) -> ImportResult:
        """Bundle the import inputs into a request and hand them to the facade."""
        request = ImportRequest(path=path, file_type=file_type, mode=mode)
        return self._facade.import_file(request)

    def generate_schedules(self, program_ids: List[str]) -> SchedulerWorker:
        """Ask the facade to start schedule generation for the selected programs."""
        return self._facade.generate(program_ids)

    def cancel_scheduling(self) -> None:
        """Ask the facade to cancel an in-progress generation run."""
        self._facade.cancel_scheduling()

    def get_schedule_view(self, index: int) -> ScheduleViewModel:
        """Get the schedule at index as a view model for the GUI to render."""
        return self._facade.get_schedule_vm(index)

    def save_schedule(self, index: int, path: str) -> None:
        """Ask the facade to export the schedule at index to the given path."""
        self._facade.export(index, path)

    def on_app_closing(self) -> None:
        """Hook for cleanup when the application window closes."""
        pass