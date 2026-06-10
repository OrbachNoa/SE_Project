"""ApplicationFacade - the single entry point for the GUI into the application.

Coordinates state, services, and view-model mapping. Holds no business
logic of its own: every operation delegates to the relevant service.
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
        """Delegate a file import request to FileImportService."""
        return self._importer.load_file(request.path, request.file_type, request.mode)
    
    def update_periods(self, edited_vms) -> None:
        """Apply edited exam periods from the calendar editor into state."""
        self._state.get_input_state().apply_period_edits(edited_vms)

    def generate(self, program_ids: List[str]) -> SchedulerWorker:
        """Start an async scheduling run for the given programs.
        
        Clears previous results, stores the selected programs, launches a
        background worker, and wires its batch signal to _on_schedules_batch_received.
        """
        # Clear previous results before starting a new run.
        self._state.get_schedule_state().set_schedules([])

        input_state = self._state.get_input_state()
        input_state.set_selected_programs(program_ids)
        # Deploy the background process worker with correct state properties
        worker = self._scheduler.generate_async(
            program_ids, input_state.get_courses(), input_state.get_periods()
        )
        
        # Wire the worker's batch signal so results are captured as they arrive.
        worker.schedules_batch_found.connect(self._on_schedules_batch_received)
        return worker

    def _on_schedules_batch_received(self, batch_size: int) -> None:
        """Slot called when the background worker persists a batch to SQLite.
        
        Receives a count rather than a list to avoid passing heavy objects
        across thread boundaries, keeping the UI responsive.
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
        """Return True if at least one schedule is available to display."""
        return self._state.get_schedule_state().is_first_window_ready()

    def get_total_count(self) -> int:
        """Return the total number of generated schedules."""
        return self._state.get_schedule_state().count()

    def load_page(self, page: int) -> None:
        """Load the given page of results into the active window."""
        self._state.get_schedule_state().load_page(page)

    def get_page_info(self) -> dict:
        """Return a dict with current pagination state for the GUI."""
        state = self._state.get_schedule_state()
        return {
            "current_page":  state.current_page,
            "total_pages":   state.total_pages(),
            "total_count":   state.count(),
            "window_size":   state.current_window_size(),
            "sqlite_count":  state.sqlite_count(),
        }

    def cancel_scheduling(self) -> None:
        """Signal the active background worker to stop."""
        self._scheduler.cancel()

    def get_schedule_vm(self, index: int) -> ScheduleViewModel:
        """Build and return a ScheduleViewModel for the schedule at the given index."""
        schedule_state = self._state.get_schedule_state()
        dto = schedule_state.get_schedule(index)
        selected = self._state.get_input_state().get_selected_programs()
        return self._mapper.to_schedule_vm(dto, current_index=index, total=schedule_state.count(), selected_programs=selected)

    def export(self, index: int, path: str) -> None:
        """Save the schedule at the given index to disk."""
        dto = self._state.get_schedule_state().get_schedule(index)
        self._exporter.save(dto, path)
