"""ApplicationFacade - the single entry point for the GUI into the application.

Coordinates the services, the runtime state, and the view-model mapper. Holds no
business logic of its own: every operation delegates to a service and, where
relevant, updates AppState or maps domain data to view models.
"""
from __future__ import annotations

from typing import List

from src.application.app_state import AppState
from src.application.file_import_service import FileImportService
from src.application.scheduling_service import SchedulingService
from src.application.schedule_export_service import ScheduleExportService
from src.application.view_model_mapper import ViewModelMapper
from src.application.import_request import ImportRequest
from src.application.import_result import ImportResult
from src.application.dto_viewmodel.schedule_view_model import ScheduleViewModel
from src.concurrency.SchedulerWorker import SchedulerWorker


class ApplicationFacade:
    """Coordinates state, file loading, scheduling, export, and view-model mapping."""

    def __init__(
        self,
        state: AppState,
        importer: FileImportService,
        scheduler: SchedulingService,
        exporter: ScheduleExportService,
        mapper: ViewModelMapper,
    ) -> None:
        self._state = state
        self._importer = importer
        self._scheduler = scheduler
        self._exporter = exporter
        self._mapper = mapper

    def import_file(self, request: ImportRequest) -> ImportResult:
        """Import one file via the import service; state is updated as a side effect.

        The import service writes parsed data into the same InputDataState this
        facade's AppState exposes, so a successful import leaves AppState current.
        """
        return self._importer.load_file(request.path, request.file_type, request.mode)

    def generate(self, program_ids: List[str]) -> SchedulerWorker:
        """Start schedule generation for the selected programs in the background.

        Wires result storage internally: each schedule the worker finds is added
        to the schedule-result state as it streams in, so callers never have to
        store DTOs themselves. The running worker is returned so the UI layer can
        connect its signals for live progress, completion, and error reporting.
        """
        # Clear previous results so a second run does not accumulate on top of the first.
        self._state.get_schedule_state().set_schedules([])

        input_state = self._state.get_input_state()
        worker = self._scheduler.generate_async(
            program_ids, input_state.get_courses(), input_state.get_periods()
        )
        # Accumulate results in state as they arrive (encapsulated here, not exposed).
        worker.schedule_found.connect(self._state.get_schedule_state().add_schedule)
        return worker

    def cancel_scheduling(self) -> None:
        """Cancel an in-progress generation run."""
        self._scheduler.cancel()

    def get_schedule_vm(self, index: int) -> ScheduleViewModel:
        """Return the schedule at index as a view model, with 'X of Y' context."""
        schedule_state = self._state.get_schedule_state()
        dto = schedule_state.get_schedule(index)
        return self._mapper.to_schedule_vm(dto, current_index=index, total=schedule_state.count())

    def export(self, index: int, path: str) -> None:
        """Export the schedule at index to the given path."""
        dto = self._state.get_schedule_state().get_schedule(index)
        self._exporter.save(dto, path)