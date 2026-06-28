"""Presentation logic for the output screen."""
from __future__ import annotations

from typing import List

from gui.features.output.PeriodNavigator import PeriodNavigator
from gui.features.output.workers.SortWorker import SortWorker

class OutputScreenPresenter:
    """Coordinates schedule paging, period navigation, display, and export guards."""

    # Initialize the presenter, connecting the view and controller to manage data and UI state
    def __init__(self, view, controller, router) -> None:
        self._view = view
        self._controller = controller
        self._router = router

        self._current_index = 0
        self._total = 0
        self._current_page = 0
        self._total_pages = 0
        self._total_found = 0
        self._sqlite_count = 0
        self._window_capacity = 10000
        self._periods = PeriodNavigator()

        # Listen for updates from the background controller regarding the total number of solutions found
        self._controller.total_count_updated.connect(self.on_total_count_updated)
        if hasattr(self._controller, "search_finished"):
            self._controller.search_finished.connect(self.on_search_finished)

        # True only while OutputScreen is the currently visible screen.
        # Guards background callbacks (SortWorker ready, search_finished) so
        # they are silently discarded when the user is on another screen.
        self._is_active = False
        self._sort_worker = None
        self._retired_sort_workers = []

    @property
    def current_index(self) -> int:
        return self._current_index

    # Update the UI counter labels and button availability based on the current solution index
    def refresh_counter(self) -> None:
        if self._total == 0:
            self._view.set_solution_counter("No solutions")
        else:
            self._view.set_solution_counter(f"Solution {self._current_index + 1} / {self._total}")

        self._view.set_solution_controls(
            can_prev=self._current_index > 0,
            can_next=self._current_index < self._total - 1,
            can_export=self._total > 0,
        )
        self.refresh_page_bar()

    # Manage pagination display, showing the current page number and availability of next/prev pages
    def refresh_page_bar(self) -> None:
        if self._total_pages <= 1:
            self._view.set_page_bar_visible(False)
            return

        next_page_index = self._current_page + 1
        rows_needed_on_disk = next_page_index * self._window_capacity
        next_page_is_ready = self._sqlite_count >= rows_needed_on_disk
        has_next = self._current_page < self._total_pages - 1

        self._view.set_page_bar(
            visible=True,
            label=f"Page {self._current_page + 1} / {self._total_pages}",
            can_first=self._current_page > 0,
            can_previous=self._current_page > 0,
            can_next=has_next and next_page_is_ready,
            can_last=has_next and next_page_is_ready,
        )

    # Respond to data updates from the controller, adjusting total counts and page information
    def on_total_count_updated(self, _total: int) -> None:
        if not self._is_active:
            return

        info = self._controller.get_page_info()
        self._total_found = info["total_count"]
        self._total_pages = info["total_pages"]
        self._sqlite_count = info.get("sqlite_count", 0)

        if self._current_page == 0:
            self._total = info["window_size"]
            self.refresh_counter()
        else:
            self.refresh_page_bar()

    # Navigation buttons for switching between database pages
    def on_next_page(self) -> None:
        self._load_page(self._current_page + 1)

    def on_prev_page(self) -> None:
        self._load_page(self._current_page - 1)

    def on_first_page(self) -> None:
        if self._current_page != 0:
            self._load_page(0)

    def on_last_page(self) -> None:
        target = self._total_pages - 1
        if target >= 0 and self._current_page != target:
            self._load_page(target)

    # Core rendering logic: retrieves current schedule data and pushes it to the UI
    def show_current(self) -> None:
        if self._total == 0:
            return

        self._view.set_screen_updates(False)
        try:
            schedule_view = self._controller.get_schedule_view(self._current_index)
            if self._periods.total == 0:
                self._periods.reset(self._get_available_periods())

            selected_period = self._periods.current_period
            if selected_period is None:
                self._view.set_period_navigation("", False, False)
                return

            self._view.set_period_navigation(
                self._periods.label(),
                self._periods.can_move_previous(),
                self._periods.can_move_next(),
            )

            # Filter assignments to match the currently viewed exam period
            filtered_items = [
                item
                for item in schedule_view.items
                if item.date and selected_period.start_date <= item.date <= selected_period.end_date
            ]
            self._view.render_calendar(
                self._periods.date_list(),
                selected_period.excluded_dates,
                filtered_items,
            )
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "render_calendar", "screen": "output"}
            )
            self._view.show_display_error(f"Failed to paint calendar: {message}")
        finally:
            self._view.set_screen_updates(True)

    # Navigation back to the input screen
    def on_back(self) -> None:
        self._router.back()

    # Initiates the PDF export process for the current schedule
    def on_export_pdf(self) -> None:
        if self._total == 0:
            self._view.show_nothing_to_export("There is no schedule to export yet.")
            return

        try:
            schedule_view = self._controller.get_schedule_view(self._current_index)
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "read_schedule", "screen": "output", "export_format": "pdf"}
            )
            self._view.show_export_error(f"Could not read the current schedule:\n{message}")
            return

        if schedule_view.is_empty():
            self._view.show_nothing_to_export("This schedule has no exams to export.")
            return

        self._view.export_schedule_pdf(schedule_view, self._current_index)

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

    # Initiates the TXT export process for the current schedule
    def on_export_txt(self) -> None:
        if self._total == 0:
            self._view.show_nothing_to_export("There is no schedule to export yet.")
            return

        try:
            schedule_view = self._controller.get_schedule_view(self._current_index)
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "read_schedule", "screen": "output", "export_format": "txt"}
            )
            self._view.show_export_error(f"Could not read the current schedule:\n{message}")
            return

        if schedule_view.is_empty():
            self._view.show_nothing_to_export("This schedule has no exams to export.")
            return

        path = self._view.ask_save_path(f"exam_schedule_solution_{self._current_index + 1}.txt")
        if not path:
            return

        try:
            self._controller.save_schedule(self._current_index, path)
            self._view.show_message(f"Saved to:\n{path}")
        except Exception as error:
            # No extra "Could not save:" prefix — the mapped message (e.g. a
            # permission failure) already says the file could not be written,
            # and the dialog title already says "Export error".
            message = self._controller.map_error(
                error, {"operation": "save_schedule", "screen": "output", "export_format": "txt", "path": path}
            )
            self._view.show_export_error(message)

    # Initiates the Excel export process for the current schedule
    def on_export_excel(self) -> None:
        if self._total == 0:
            self._view.show_nothing_to_export("There is no schedule to export yet.")
            return

        try:
            schedule_view = self._controller.get_schedule_view(self._current_index)
        except Exception as error:
            message = self._controller.map_error(
                error, {"operation": "read_schedule", "screen": "output", "export_format": "excel"}
            )
            self._view.show_export_error(f"Could not read the current schedule:\n{message}")
            return

        if schedule_view.is_empty():
            self._view.show_nothing_to_export("This schedule has no exams to export.")
            return

        path = self._view.ask_save_path_excel(f"exam_schedule_solution_{self._current_index + 1}.xlsx")
        if not path:
            return

        try:
            self._controller.save_schedule_excel(self._current_index, path)
            self._view.show_message(f"Saved to:\n{path}")
        except Exception as error:
            # PermissionErrorMapper already produces a friendly "file is open
            # elsewhere" message, so there is no need for a separate
            # `except PermissionError` here — one path covers every failure.
            message = self._controller.map_error(
                error, {"operation": "save_schedule", "screen": "output", "export_format": "excel", "path": path}
            )
            self._view.show_export_error(message)

    # Navigation helpers for period blocks and solution indices
    def on_prev_period(self) -> None:
        if self._periods.move_previous():
            self.show_current()

    def on_next_period(self) -> None:
        if self._periods.move_next():
            self.show_current()

    def on_next_solution(self) -> None:
        if self._current_index < self._total - 1:
            self._current_index += 1
            self.show_current()
            self.refresh_counter()

    def on_prev_solution(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            self.show_current()
            self.refresh_counter()

    # Logic for jumping to a specific solution by number
    def on_jump_to_solution(self) -> None:
        """Jump to a specific solution number entered by the user."""
        try:
            input_text = self._view.get_jump_to_value().strip()
            if not input_text:
                return
            
            solution_num = int(input_text)
            # Convert from 1-based (user input) to 0-based (code index)
            target_index = solution_num - 1
            
            if target_index < 0 or target_index >= self._total:
                self._view.show_display_error(
                    f"Invalid solution number. Please enter a number between 1 and {self._total}."
                )
                return
            
            self._current_index = target_index
            self.show_current()
            self.refresh_counter()
        except ValueError:
            self._view.show_display_error("Please enter a valid number")

    # Initial setup steps when navigating to this screen
    def on_enter(self) -> None:
        self._is_active = True
        self._current_index = 0
        self._sync_page_info()
        self._periods.reset(self._get_available_periods())
        self.show_current()
        self.refresh_counter()
        self._view.focus_back_button()

    def on_leave(self) -> None:
        """Called when the user navigates away from the OutputScreen.

        Marks the screen as inactive so that background callbacks
        (SortWorker ready/failed, search_finished, total_count_updated)
        are silently discarded instead of touching state that may have
        been reset by a new generation run on the InputScreen.
        """
        self._is_active = False
        # Stop any background sort still running so its signals are not
        # delivered to a screen the user has already left.
        _w = self._sort_worker
        if _w is not None and _w.isRunning():
            try:
                _w.ready.disconnect(self._on_sort_ready)
                _w.failed.disconnect(self._on_sort_failed)
            except (RuntimeError, TypeError):
                pass
            _w.quit()
            self._retired_sort_workers.append(_w)
            _w.finished.connect(lambda _w=_w: self._cleanup_retired_sort_worker(_w))
        self._sort_worker = None

    def _cleanup_retired_sort_worker(self, worker) -> None:
        try:
            self._retired_sort_workers.remove(worker)
        except ValueError:
            pass
        try:
            worker.deleteLater()
        except RuntimeError:
            pass

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
            self._sync_page_info()
            self._current_index = 0
            self.show_current()
            self.refresh_counter()
            return

        self._view.set_sorting_busy(True) if hasattr(self._view, "set_sorting_busy") else None
        self._sort_worker = SortWorker(self._controller, priority_list)
        self._sort_worker.ready.connect(self._on_sort_ready)
        self._sort_worker.failed.connect(self._on_sort_failed)
        self._sort_worker.start()

    def _on_sort_ready(self, data: dict) -> None:
        """Background sort finished — apply it on the GUI thread (fast)."""
        if not self._is_active:
            # User navigated away before the worker finished so sorting isnt needed.
            return
        self._controller.apply_sort_data(data)
        if hasattr(self._view, "set_sorting_busy"):
            self._view.set_sorting_busy(False)
        self._sync_page_info()
        self._current_index = 0
        self.show_current()
        self.refresh_counter()

    def _on_sort_failed(self, message: str) -> None:
        """Background sort failed — clear the busy state and surface the error."""
        if hasattr(self._view, "set_sorting_busy"):
            self._view.set_sorting_busy(False)
        if hasattr(self._view, "show_error"):
            self._view.show_error(f"Sorting failed: {message}")
        if self._sort_worker is not None:
            self._controller.log_worker_error(self._sort_worker.last_error)

    def on_search_finished(self) -> None:
        """Refresh the UI when schedule generation is finished.

        If a sort is active, the final global re-sort (to include schedules
        produced after the user sorted) runs on the SAME background worker as
        Apply, so generation-end doesn't freeze the GUI. If no sort is active,
        just refresh the view.
        """
        # User may have left while generation was running so no new searches are needed
        if not self._is_active:
            return
        active = []
        if hasattr(self._controller, "get_active_sort_priority"):
            active = self._controller.get_active_sort_priority() or []
        if active and hasattr(self._controller, "compute_sort_data"):
            # background re-sort, identical path to Apply
            if hasattr(self._view, "set_sorting_busy"):
                self._view.set_sorting_busy(True)
            self._sort_worker = SortWorker(self._controller, active)
            self._sort_worker.ready.connect(self._on_sort_ready)
            self._sort_worker.failed.connect(self._on_sort_failed)
            self._sort_worker.start()
            return
        self._sync_page_info()
        self._current_index = 0
        self.show_current()
        self.refresh_counter()

    # Load a specific data page from the database
    def _load_page(self, target: int) -> None:
        if target < 0 or target >= self._total_pages:
            return

        self._controller.load_page(target)
        self._sync_page_info()
        self._current_index = 0
        self.show_current()
        self.refresh_counter()

    # Helper to sync internal state with controller's page tracking
    def _sync_page_info(self) -> None:
        info = self._controller.get_page_info()
        self._current_page = info["current_page"]
        self._total_pages = info["total_pages"]
        self._total = info["window_size"]
        self._total_found = info["total_count"]
        self._sqlite_count = info.get("sqlite_count", 0)
        self._window_capacity = info.get("window_capacity", 10000)

    # Retrieve period configurations from the controller
    def _get_available_periods(self):
        periods = self._controller.get_loaded_periods()
        mapper = self._controller.get_mapper()
        if mapper and periods:
            return mapper.to_period_edit_vms(periods)
        return []
