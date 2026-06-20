"""Presentation logic for the output screen."""
from __future__ import annotations

from typing import List

from gui.features.output.PeriodNavigator import PeriodNavigator
from src.gui.features.output.workers.SortWorker import SortWorker
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
            self._view.show_display_error(f"Failed to paint calendar: {error}")
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
            self._view.show_export_error(f"Could not read the current schedule:\n{error}")
            return

        if schedule_view.is_empty():
            self._view.show_nothing_to_export("This schedule has no exams to export.")
            return

        self._view.export_schedule_pdf(schedule_view, self._current_index)

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
        self._current_index = 0
        self._sync_page_info()
        self._periods.reset(self._get_available_periods())
        self.show_current()
        self.refresh_counter()
        self._view.focus_back_button()

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

    def on_search_finished(self) -> None:
        """Refresh the UI when schedule generation is finished."""
        # Generation is done — run the global sort once now (it was skipped
        # during generation to keep the GUI responsive). No-op if no sort active.
        if hasattr(self._controller, "refresh_sort"):
            self._controller.refresh_sort()
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