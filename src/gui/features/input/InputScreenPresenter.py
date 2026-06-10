"""Presentation logic for the input screen."""
from __future__ import annotations

from typing import List

from src.application.ImportBoundary import ImportMode


# This class is the "brain" for the Input screen. It handles all the logic,
# listens for events, and tells the UI (View) what to display.
class InputScreenPresenter:
    """Coordinates file import, validation, scheduler lifecycle, and navigation."""

    # Connects the UI to the controller and defines the initial state of the screen
    def __init__(self, view, controller, router, output_screen_name: str) -> None:
        self._view = view
        self._controller = controller
        self._router = router
        self._output_screen_name = output_screen_name

        self._courses_loaded = False
        self._periods_loaded = False
        self._last_count = 0
        self._already_navigated = False

        # Listen for signals coming from the background controller (like when a search finishes)
        self._controller.schedule_found.connect(self.on_schedule_found)
        self._controller.progress_updated.connect(self.on_progress_updated)
        self._controller.search_finished.connect(self.on_search_finished)
        self._controller.error_occurred.connect(self.on_error_occurred)
        self._controller.early_results_ready.connect(self.on_early_results_ready)

    # Checks if all required files are loaded and updates the "Generate" button's state accordingly
    def refresh_generate_button(self) -> None:
        missing = []
        if not self._courses_loaded:
            missing.append("courses file")
        if not self._periods_loaded:
            missing.append("periods file")

        tooltip = ""
        if missing:
            tooltip = "Please load: " + " and ".join(missing) + " to continue."

        self._view.set_generate_button_state(len(missing) == 0, tooltip)
        self._view.set_validation_message("")
        self.validate_programs()

    # Determines if the user wants to completely replace or update existing data
    def selected_mode(self) -> ImportMode:
        return ImportMode.REPLACE if self._view.is_replace_mode_selected() else ImportMode.UPDATE

    # Triggered when the user clicks the "Load Courses" button in the UI
    def on_load_courses_clicked(self) -> None:
        self.on_load_courses(self.selected_mode())

    # Triggered when the user clicks the "Load Periods" button in the UI
    def on_load_periods_clicked(self) -> None:
        self.on_load_periods(self.selected_mode())

    # Handles the actual file loading process for courses
    def on_load_courses(self, mode: ImportMode) -> None:
        path = self._view.prompt_for_file("Select courses file", "All files (*)")
        if not path:
            return

        result = self._controller.load_file(path, "courses", mode)
        if not self._handle_import_result(result, "courses"):
            return

        self._courses_loaded = True
        self._view.mark_courses_loaded(result.loaded_count)
        self.refresh_generate_button()

        # After loading, get the data and tell the UI to render the course list
        courses = self._controller.get_loaded_courses()
        mapper = self._controller.get_mapper()
        if courses and mapper is not None:
            self._view.render_courses(mapper.to_program_courses_vm(courses))

    # Handles the actual file loading process for periods
    def on_load_periods(self, mode: ImportMode) -> None:
        path = self._view.prompt_for_file("Select periods file", "All files (*)")
        if not path:
            return

        result = self._controller.load_file(path, "periods", mode)
        if not self._handle_import_result(result, "periods"):
            return

        self._periods_loaded = True
        self._view.mark_periods_loaded(result.loaded_count)
        self.refresh_generate_button()

        # After loading, show the period editor if data is valid
        periods = self._controller.get_loaded_periods()
        mapper = self._controller.get_mapper()
        if not periods or mapper is None:
            return

        period_vms = mapper.to_period_edit_vms(periods)
        if period_vms:
            self._view.show_period_editor(period_vms)

    # Starts the scheduling process in the background controller
    def on_generate_clicked(self) -> None:
        if not self.validate_programs():
            return

        self._already_navigated = False
        self._set_running_mode(True)
        self._controller.generate_schedules(self._collect_selected_program_ids())

    # Stops the scheduling process if the user clicks cancel
    def on_cancel_clicked(self) -> None:
        self._controller.cancel_scheduling()
        self._set_running_mode(False)
        self._view.set_progress_text("")

    # Navigate to the results screen
    def on_view_results_clicked(self) -> None:
        self._router.show(self._output_screen_name)

    # Updates the exam period constraints in the controller
    def on_constraints_saved(self, updated_vms: list) -> None:
        self._controller.update_exam_periods(updated_vms)
        self.refresh_generate_button()

    def on_schedule_found(self, dto) -> None:
        pass

    # Updates the progress label while the scheduler is running
    def on_progress_updated(self, count: int) -> None:
        self._last_count = count
        suffix = "s" if count != 1 else ""
        self._view.set_progress_text(f"Found {count} schedule{suffix} so far...")

    # Automatically switches to the output screen as soon as valid results are ready
    def on_early_results_ready(self) -> None:
        self._navigate_to_output()

    # Handles what happens when the scheduling search is fully finished
    def on_search_finished(self) -> None:
        self._set_running_mode(False)
        if self._already_navigated:
            return

        if self._result_count() > 0:
            self._navigate_to_output()
        else:
            self._view.set_validation_message(
                "No valid schedules found. Try adjusting programs or exam dates."
            )

    # Shows an error message if something went wrong during scheduling
    def on_error_occurred(self, message: str) -> None:
        self._set_running_mode(False)
        self._view.show_scheduler_error(message)

    # Ensures the generate button is in the right state when entering the screen
    def on_enter(self) -> None:
        self.refresh_generate_button()

    # Helper: gathers all currently selected program IDs from the UI
    def _collect_selected_program_ids(self) -> List[str]:
        return self._view.selected_program_ids()

    # Checks if the user has selected at least one program
    def validate_programs(self) -> bool:
        if not self._collect_selected_program_ids():
            self._view.set_program_error("Please select at least one study program.")
            return False

        self._view.set_program_error("")
        return True

    # Updates UI elements based on whether the scheduler is currently "running" or "idle"
    def _set_running_mode(self, running: bool) -> None:
        if running:
            self._last_count = 0
            self._view.set_running_mode(True, "Initialising scheduler...")
            self._view.set_view_results_visible(False)
        else:
            self._view.set_running_mode(False, "")

    # Navigates to the output screen only once
    def _navigate_to_output(self) -> None:
        if self._already_navigated:
            return

        self._already_navigated = True
        self._view.set_view_results_visible(True)
        self._router.show(self._output_screen_name)

    # Gets the total number of schedules found so far from the controller
    def _result_count(self) -> int:
        try:
            info = self._controller.get_page_info()
            return int(info.get("total_count", 0))
        except Exception:
            return self._last_count

    # Handles and displays errors that happen during file import
    def _handle_import_result(self, result, data_label: str) -> bool:
        if result.success:
            return True

        detail = "\n".join(result.errors) if result.errors else "Unknown error."
        self._view.show_import_error(data_label, detail)
        return False