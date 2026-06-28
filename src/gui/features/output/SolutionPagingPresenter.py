"""Coordinates solution/page navigation and calendar rendering for the output screen.

Owns the current solution index, the loaded page window, and period
navigation — the result-paging concern split out of OutputScreenPresenter.
Knows nothing about sorting or export; OutputScreenPresenter wires those
collaborators in separately.
"""
from __future__ import annotations

from gui.features.output.PeriodNavigator import PeriodNavigator
from src.config import WINDOW_SIZE


class SolutionPagingPresenter:
    """Owns paging/solution-index state and renders the current schedule."""

    def __init__(self, view, controller) -> None:
        self._view = view
        self._controller = controller

        self.current_index = 0
        self.total = 0
        self.current_page = 0
        self.total_pages = 0
        self.total_found = 0
        self.sqlite_count = 0
        self.window_capacity = WINDOW_SIZE
        self.periods = PeriodNavigator()

    # Update the UI counter labels and button availability based on the current solution index
    def refresh_counter(self) -> None:
        if self.total == 0:
            self._view.set_solution_counter("No solutions")
        else:
            # The solution controls navigate only inside the currently loaded
            # database window; the page bar is responsible for global position.
            self._view.set_solution_counter(
                f"Solution {self.current_index + 1:,} / {self.total:,}"
            )

        self._view.set_solution_controls(
            can_prev=self.current_index > 0,
            can_next=self.current_index < self.total - 1,
            can_export=self.total > 0,
        )
        self.refresh_page_bar()

    # Manage pagination display, showing the current page number and availability of next/prev pages
    def refresh_page_bar(self) -> None:
        if self.total_pages <= 1:
            self._view.set_page_bar_visible(False)
            return

        next_page_index = self.current_page + 1
        rows_needed_on_disk = next_page_index * self.window_capacity
        next_page_is_ready = self.sqlite_count >= rows_needed_on_disk
        has_next = self.current_page < self.total_pages - 1

        self._view.set_page_bar(
            visible=True,
            label=f"Page {self.current_page + 1} / {self.total_pages}",
            can_first=self.current_page > 0,
            can_previous=self.current_page > 0,
            can_next=has_next and next_page_is_ready,
            can_last=has_next and next_page_is_ready,
        )

    # Refresh total/page counts from the controller (called on total_count_updated).
    def on_total_count_updated(self) -> None:
        info = self._controller.get_page_info()
        self.total_found = info["total_count"]
        self.total_pages = info["total_pages"]
        self.sqlite_count = info.get("sqlite_count", 0)

        if self.current_page == 0:
            self.total = info["window_size"]
            self.refresh_counter()
        else:
            self.refresh_page_bar()

    # Navigation buttons for switching between database pages
    def on_next_page(self) -> None:
        self._load_page(self.current_page + 1)

    def on_prev_page(self) -> None:
        self._load_page(self.current_page - 1)

    def on_first_page(self) -> None:
        if self.current_page != 0:
            self._load_page(0)

    def on_last_page(self) -> None:
        target = self.total_pages - 1
        if target >= 0 and self.current_page != target:
            self._load_page(target)

    # Core rendering logic: retrieves current schedule data and pushes it to the UI
    def show_current(self) -> None:
        if self.total == 0:
            return

        self._view.set_screen_updates(False)
        try:
            schedule_view = self._controller.get_schedule_view(self.current_index)
            if self.periods.total == 0:
                self.periods.reset(self._get_available_periods())

            selected_period = self.periods.current_period
            if selected_period is None:
                self._view.set_period_navigation("", False, False)
                return

            self._view.set_period_navigation(
                self.periods.label(),
                self.periods.can_move_previous(),
                self.periods.can_move_next(),
            )

            # Filter assignments to match the currently viewed exam period
            filtered_items = [
                item
                for item in schedule_view.items
                if item.date and selected_period.start_date <= item.date <= selected_period.end_date
            ]
            self._view.render_calendar(
                self.periods.date_list(),
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

    # Navigation helpers for period blocks and solution indices
    def on_prev_period(self) -> None:
        if self.periods.move_previous():
            self.show_current()

    def on_next_period(self) -> None:
        if self.periods.move_next():
            self.show_current()

    def on_next_solution(self) -> None:
        if self.current_index < self.total - 1:
            self.current_index += 1
            self.show_current()
            self.refresh_counter()

    def on_prev_solution(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
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

            if target_index < 0 or target_index >= self.total:
                self._view.show_display_error(
                    f"Invalid solution number. Please enter a number between 1 and {self.total}."
                )
                return

            self.current_index = target_index
            self.show_current()
            self.refresh_counter()
        except ValueError:
            self._view.show_display_error("Please enter a valid number")

    # Reset paging state for a fresh screen visit and render the first solution.
    def enter(self) -> None:
        self.current_index = 0
        self._sync_page_info()
        self.periods.reset(self._get_available_periods())
        self.show_current()
        self.refresh_counter()

    # Re-sync from the controller and jump back to the first solution (after a sort/page change).
    def reset_to_first(self) -> None:
        self._sync_page_info()
        self.current_index = 0
        self.show_current()
        self.refresh_counter()

    # Load a specific data page from the database
    def _load_page(self, target: int) -> None:
        if target < 0 or target >= self.total_pages:
            return

        self._controller.load_page(target)
        self._sync_page_info()
        self.current_index = 0
        self.show_current()
        self.refresh_counter()

    # Helper to sync internal state with controller's page tracking
    def _sync_page_info(self) -> None:
        info = self._controller.get_page_info()
        self.current_page = info["current_page"]
        self.total_pages = info["total_pages"]
        self.total = info["window_size"]
        self.total_found = info["total_count"]
        self.sqlite_count = info.get("sqlite_count", 0)
        self.window_capacity = info.get("window_capacity", WINDOW_SIZE)

    # Retrieve period configurations from the controller
    def _get_available_periods(self):
        periods = self._controller.get_loaded_periods()
        mapper = self._controller.get_mapper()
        if mapper and periods:
            return mapper.to_period_edit_vms(periods)
        return []
