"""Presentation logic for the output screen."""
from __future__ import annotations

from typing import List

from gui.common.ScheduleExportMixin import ScheduleExportMixin
from gui.features.output.SolutionPagingPresenter import SolutionPagingPresenter
from gui.features.output.SortLifecyclePresenter import SortLifecyclePresenter


class OutputScreenPresenter(ScheduleExportMixin):
    """Coordinates the output screen.

    Each concern lives in its own collaborator — paging/display
    (SolutionPagingPresenter), background sort threads (SortLifecyclePresenter),
    and export (ScheduleExportMixin). This class owns only the screen's
    active/inactive lifecycle and the glue between controller signals and the
    right collaborator; it does not hold paging or sort state itself.
    """

    # Initialize the presenter, connecting the view and controller to manage data and UI state
    def __init__(self, view, controller, router) -> None:
        self._view = view
        self._controller = controller
        self._router = router

        self._paging = SolutionPagingPresenter(view, controller)
        self._sort = SortLifecyclePresenter(controller)

        # Listen for updates from the background controller regarding the total number of solutions found
        self._controller.total_count_updated.connect(self.on_total_count_updated)
        if hasattr(self._controller, "search_finished"):
            self._controller.search_finished.connect(self.on_search_finished)

        # True only while OutputScreen is the currently visible screen.
        # Guards background callbacks (SortWorker ready, search_finished) so
        # they are silently discarded when the user is on another screen.
        self._is_active = False

    # ── compatibility accessors ──────────────────────────────────────────────
    # Existing unit tests construct this presenter directly and poke its
    # private state (e.g. `presenter._total = 5`) instead of going through the
    # paging/sort collaborators. These properties forward to the real owner of
    # that state so the public/private contract this presenter already had
    # keeps working, while the state itself genuinely lives in one place.
    @property
    def current_index(self) -> int:
        return self._paging.current_index

    @property
    def _current_index(self) -> int:
        return self._paging.current_index

    @_current_index.setter
    def _current_index(self, value: int) -> None:
        self._paging.current_index = value

    @property
    def _total(self) -> int:
        return self._paging.total

    @_total.setter
    def _total(self, value: int) -> None:
        self._paging.total = value

    @property
    def _current_page(self) -> int:
        return self._paging.current_page

    @_current_page.setter
    def _current_page(self, value: int) -> None:
        self._paging.current_page = value

    @property
    def _total_pages(self) -> int:
        return self._paging.total_pages

    @_total_pages.setter
    def _total_pages(self, value: int) -> None:
        self._paging.total_pages = value

    @property
    def _sqlite_count(self) -> int:
        return self._paging.sqlite_count

    @_sqlite_count.setter
    def _sqlite_count(self, value: int) -> None:
        self._paging.sqlite_count = value

    @property
    def _periods(self):
        return self._paging.periods

    @property
    def _sort_worker(self):
        return self._sort.worker

    @_sort_worker.setter
    def _sort_worker(self, value) -> None:
        self._sort.worker = value

    @property
    def _retired_sort_workers(self) -> list:
        return self._sort.retired_workers

    # ── paging/display, delegated to SolutionPagingPresenter ────────────────
    def refresh_counter(self) -> None:
        self._paging.refresh_counter()

    def refresh_page_bar(self) -> None:
        self._paging.refresh_page_bar()

    def on_total_count_updated(self, _total: int) -> None:
        if not self._is_active:
            return
        self._paging.on_total_count_updated()

    def on_next_page(self) -> None:
        self._paging.on_next_page()

    def on_prev_page(self) -> None:
        self._paging.on_prev_page()

    def on_first_page(self) -> None:
        self._paging.on_first_page()

    def on_last_page(self) -> None:
        self._paging.on_last_page()

    def show_current(self) -> None:
        self._paging.show_current()

    def on_prev_period(self) -> None:
        self._paging.on_prev_period()

    def on_next_period(self) -> None:
        self._paging.on_next_period()

    def on_next_solution(self) -> None:
        self._paging.on_next_solution()

    def on_prev_solution(self) -> None:
        self._paging.on_prev_solution()

    def on_jump_to_solution(self) -> None:
        self._paging.on_jump_to_solution()

    # ── navigation ────────────────────────────────────────────────────────────
    def on_back(self) -> None:
        self._router.back()

    # The current sort priority, used by the view to pre-fill the sort panel.
    def get_current_sort_priority(self):
        return self._controller.get_current_sort_priority()

    # Navigate to the cluster overview screen (registered as "clusters").
    def open_clusters(self) -> None:
        # Entering clustering from the results screen is the one doorway in, so
        # discard any cached session here: the overview then re-clusters fresh on
        # the results loaded so far, instead of showing a stale computation from
        # before more schedules streamed in.
        self._controller.invalidate_clustering()
        self._router.show("clusters")

    # ── export hooks for ScheduleExportMixin ─────────────────────────────────
    def _export_has_content(self) -> bool:
        return self._paging.total != 0

    def _export_read_schedule(self):
        return self._controller.get_schedule_view(self._paging.current_index)

    def _export_filename(self, ext: str) -> str:
        return f"exam_schedule_solution_{self._paging.current_index + 1}.{ext}"

    def _export_pdf_view(self, schedule_view) -> None:
        self._view.export_schedule_pdf(schedule_view, self._paging.current_index)

    def _export_save_txt(self, path: str) -> None:
        self._controller.save_schedule(self._paging.current_index, path)

    def _export_save_excel(self, path: str) -> None:
        self._controller.save_schedule_excel(self._paging.current_index, path)

    def _export_nothing(self, message: str) -> None:
        self._view.show_nothing_to_export(message)

    def _export_read_error(self, error: Exception, fmt: str) -> None:
        message = self._controller.map_error(
            error, {"operation": "read_schedule", "screen": "output", "export_format": fmt}
        )
        self._view.show_export_error(f"Could not read the current schedule:\n{message}")

    def _export_save_error(self, error: Exception, fmt: str, path: str) -> None:
        # No extra "Could not save:" prefix — the mapped message (e.g. a
        # permission failure) already says the file could not be written, and the
        # dialog title already says "Export error".
        message = self._controller.map_error(
            error, {"operation": "save_schedule", "screen": "output", "export_format": fmt, "path": path}
        )
        self._view.show_export_error(message)

    def _export_saved(self, path: str) -> None:
        self._view.show_message(f"Saved to:\n{path}")

    def map_export_error(self, error: Exception, path: str) -> str:
        """Map a PDF-writing failure (called by SchedulePdfExporter) to a clean message.

        The actual HTML/Qt-printing step happens inside the view-layer PDF
        exporter, outside any try/except this presenter runs — this gives it
        a way back to the same controller.map_error used by every other
        export path, instead of showing a raw exception in its own dialog.
        """
        return self._controller.map_error(
            error, {"operation": "export_pdf", "screen": "output", "export_format": "pdf", "path": path}
        )

    # ── screen lifecycle ──────────────────────────────────────────────────────
    def on_enter(self) -> None:
        self._is_active = True
        self._paging.enter()
        self._view.focus_back_button()

    def on_leave(self) -> None:
        """Called when the user navigates away from the OutputScreen.

        Marks the screen as inactive so that background callbacks
        (SortWorker ready/failed, search_finished, total_count_updated)
        are silently discarded instead of touching state that may have
        been reset by a new generation run on the InputScreen, and retires
        any sort worker still running so its signals are never delivered to
        a screen the user has already left.
        """
        self._is_active = False
        self._sort.stop()

    # ── sort lifecycle glue ──────────────────────────────────────────────────
    # Decides what should happen once a sort completes (re-sync paging and
    # re-render); the actual QThread bookkeeping lives in SortLifecyclePresenter.
    def on_sort_config_changed(self, priority_list: List[str]) -> None:
        """Called when sorting priority is updated and applied from the SortConfigPanel.

        The heavy sort runs on a background SortWorker so the GUI stays responsive
        (Apply no longer freezes). The result is applied back on the GUI thread.
        """
        if hasattr(self._controller, "save_sort_config"):
            self._controller.save_sort_config(priority_list)

        # If the controller doesn't support the background path, fall back to the
        # old synchronous apply so nothing breaks.
        if not hasattr(self._controller, "compute_sort_data"):
            if hasattr(self._controller, "apply_sort_config"):
                self._controller.apply_sort_config(priority_list)
            self._paging.reset_to_first()
            return

        if hasattr(self._view, "set_sorting_busy"):
            self._view.set_sorting_busy(True)
        self._start_sort(priority_list)

    def _start_sort(self, priority_list: List[str]) -> None:
        worker = self._sort.start(priority_list)
        worker.ready.connect(self._on_sort_ready)
        worker.failed.connect(self._on_sort_failed)
        worker.start()

    def _on_sort_ready(self, data: dict) -> None:
        """Background sort finished — apply it on the GUI thread (fast)."""
        if not self._is_active:
            # User navigated away before the worker finished so sorting isnt needed.
            return
        self._controller.apply_sort_data(data)
        if hasattr(self._view, "set_sorting_busy"):
            self._view.set_sorting_busy(False)
        self._paging.reset_to_first()

    def _on_sort_failed(self, message: str) -> None:
        """Background sort failed — clear the busy state and surface the error."""
        if hasattr(self._view, "set_sorting_busy"):
            self._view.set_sorting_busy(False)
        if hasattr(self._view, "show_error"):
            self._view.show_error(f"Sorting failed: {message}")
        if self._sort.worker is not None:
            self._controller.log_worker_error(self._sort.last_error)

    def on_search_finished(self) -> None:
        """Refresh the UI when schedule generation is finished.

        If a sort is active, the final global re-sort (to include schedules
        produced after the user sorted) runs on the SAME background worker as
        Apply, so generation-end doesn't freeze the GUI. If no sort is active,
        just refresh the view.
        """
        # Ignore the completion callback if the user already left this screen.
        if not self._is_active:
            return
        active = []
        if hasattr(self._controller, "get_active_sort_priority"):
            active = self._controller.get_active_sort_priority() or []
        if active and hasattr(self._controller, "compute_sort_data"):
            # background re-sort, identical path to Apply
            if hasattr(self._view, "set_sorting_busy"):
                self._view.set_sorting_busy(True)
            self._start_sort(active)
            return
        self._paging.reset_to_first()
