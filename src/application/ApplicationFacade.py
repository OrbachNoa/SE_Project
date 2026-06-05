"""ApplicationFacade - the single entry point for the GUI into the application.

Coordinates the services, the runtime state, and the view-model mapper. Holds no
business logic of its own: every operation delegates to a service and, where
relevant, updates AppState or maps domain data to view models.
"""
from __future__ import annotations

from typing import List

from src.application.state.AppState import AppState
from src.application.services.FileImportService import FileImportService
from src.application.services.SchedulingService import SchedulingService
from src.application.services.ScheduleExportService import ScheduleExportService
from src.application.services.ViewModelMapper import ViewModelMapper
from src.application.ImportBoundary import ImportRequest, ImportResult
from src.application.viewmodels.ScheduleViewModel import ScheduleViewModel
from src.infrastructure.concurrency.SchedulerWorker import SchedulerWorker


class ApplicationFacade:
    """Coordinates state buffers, file loading parsers, scheduling engines, and view-model mapping integrations."""

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
        """Imports a single data asset file using the parsing engine; internal state registers adapt accordingly."""
        return self._importer.load_file(request.path, request.file_type, request.mode)
    
    def update_periods(self, edited_vms) -> None:
        """Apply edited exam periods from the calendar editor into state."""
        self._state.get_input_state().apply_period_edits(edited_vms)

    def generate(self, program_ids: List[str]) -> SchedulerWorker:
        """
        Launches the scheduling computation pipeline asynchronously inside a dedicated background process thread.
        Clears out stale operational states prior to startup execution to prevent data bleeding across multiple runs.
        """
        # Clear previous run data to ensure a completely clean execution target context
        self._state.get_schedule_state().set_schedules([])

        # Extract required input parameters cached inside the state layer
        input_state = self._state.get_input_state()
        
        # Deploy the background process worker with correct state properties
        worker = self._scheduler.generate_async(
            program_ids, input_state.get_courses(), input_state.get_periods()
        )
        
        # Connect the asynchronous stream notification line to capture batch updates live
        worker.schedules_batch_found.connect(self._on_schedules_batch_received)
        return worker

    def _on_schedules_batch_received(self, batch_size: int) -> None:
        """
        Internal receiver slot triggered whenever the background process writer persists a data packet frame to SQLite.
        Accepts a scalar integer primitive size tracker instead of heavy list instances to guarantee high UI rendering speeds.
        """
        self._state.get_schedule_state().add_schedules_batch(batch_size)
        
    def get_loaded_courses(self) -> list:
        """Return the courses currently loaded in state (for display)."""
        return self._state.get_input_state().get_courses()

    def get_loaded_periods(self) -> list:
        """Return the exam periods currently loaded in state (for display)."""
        return self._state.get_input_state().get_periods()

    def get_mapper(self):
        """Return the ViewModelMapper for the GUI to build view models."""
        return self._mapper

    # ------------------------------------------------------------------
    # Page navigation 
    # ------------------------------------------------------------------

    def is_first_window_ready(self) -> bool:
        """Validates if initial data slices have reached storage, declaring it safe to pop open output view panels."""
        return self._state.get_schedule_state().is_first_window_ready()

    def get_total_count(self) -> int:
        """Fetches the aggregated volume size metrics of all valid schedules recorded across the active repository."""
        return self._state.get_schedule_state().count()

    def load_page(self, page: int) -> None:
        """Instructs the lower storage layer state targets to rotate active navigation frames over to the specified page index."""
        self._state.get_schedule_state().load_page(page)

    def get_page_info(self) -> dict:
        """Extracts a structural configuration dictionary detailing current navigation pagination thresholds for UI binding components."""
        state = self._state.get_schedule_state()
        return {
            "current_page":  state.current_page,
            "total_pages":   state.total_pages(),
            "total_count":   state.count(),
            "window_size":   state.current_window_size(),
            "sqlite_count":  state.sqlite_count(),
        }

    def cancel_scheduling(self) -> None:
        """Signals active running asynchronous worker processes to terminate operational procedures immediately."""
        self._scheduler.cancel()

    def get_schedule_vm(self, index: int) -> ScheduleViewModel:
        """Resolves raw data structures into fully localized display ViewModels, stamping context metrics on the fly."""
        schedule_state = self._state.get_schedule_state()
        dto = schedule_state.get_schedule(index)
        return self._mapper.to_schedule_vm(dto, current_index=index, total=schedule_state.count())

    def export(self, index: int, path: str) -> None:
        """Routes targeted on-memory result profiles directly out towards concrete disk serialization endpoints."""
        dto = self._state.get_schedule_state().get_schedule(index)
        self._exporter.save(dto, path)
